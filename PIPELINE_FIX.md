# Исправление пайплайна торгового бота

## Проблема
Пайплайн застревает после сканирования и не переходит к следующим состояниям (LEVEL_BUILDING → SIGNAL_WAIT → SIZING → EXECUTION).

## Корневая причина
Главный цикл движка (`_main_trading_loop` в `engine.py`) применяет задержку **ПЕРЕД** обработкой нового состояния, а не после. Это приводит к тому, что:

1. После сканирования (SCANNING → LEVEL_BUILDING) цикл спит 5 секунд
2. После пробуждения обрабатывает LEVEL_BUILDING → мгновенно переходит к SIGNAL_WAIT
3. Снова спит (теперь уже для LEVEL_BUILDING)
4. Процесс замедляется и теряется динамика

## Решение

### 1. Изменить логику задержки в главном цикле

Вместо применения задержки в **конце** цикла (после обработки), применять её **сразу после перехода состояния**.

### 2. Добавить немедленную обработку новых состояний

Если состояние изменилось во время обработки цикла, немедленно обработать новое состояние без задержки.

### 3. Оптимизировать задержки для быстрых переходов

- SCANNING → LEVEL_BUILDING: без задержки
- LEVEL_BUILDING → SIGNAL_WAIT: без задержки  
- SIGNAL_WAIT → SIZING: без задержки
- SIZING → EXECUTION: минимальная задержка (0.1s)

## Исправленный код

```python
async def _main_trading_loop(self):
    """Главный торговый цикл."""
    logger.info("Starting main trading loop...")
    
    while self.running:
        try:
            cycle_start = time.time()
            previous_state = self.state_machine.current_state
            
            if self.state_machine.is_terminal_state():
                logger.info(f"Terminal state reached: {self.state_machine.current_state.value}")
                break
            
            # Health and kill switch checks
            # ... (оставить без изменений)
            
            # Execute trading cycle
            if hasattr(self, '_execute_state_cycle'):
                await self._execute_state_cycle()
            else:
                await self.trading_orchestrator.start_trading_cycle(self.exchange_client)
            
            self.cycle_count += 1
            cycle_time = time.time() - cycle_start
            
            # Update cache
            if self.cycle_count % 10 == 0 or (time.time() - self._last_cache_update) > 5:
                self._update_cache()
            
            # Log progress
            if self.cycle_count % 10 == 0:
                logger.info(
                    f"Completed {self.cycle_count} cycles, "
                    f"state: {self.state_machine.current_state.value}, "
                    f"cycle_time: {cycle_time:.2f}s"
                )
            
            # ⚡ ИСПРАВЛЕНИЕ: Проверить, изменилось ли состояние
            current_state = self.state_machine.current_state
            state_changed = (current_state != previous_state)
            
            # ⚡ ИСПРАВЛЕНИЕ: Если состояние изменилось, обработать сразу без задержки
            if state_changed:
                # Немедленные переходы (без задержки)
                if current_state in [
                    TradingState.LEVEL_BUILDING,
                    TradingState.SIGNAL_WAIT,
                    TradingState.SIZING
                ]:
                    logger.debug(f"State changed: {previous_state.value} → {current_state.value}, continuing immediately")
                    continue  # Немедленно обработать новое состояние
                    
                # Минимальная задержка для исполнения
                elif current_state == TradingState.EXECUTION:
                    await asyncio.sleep(0.1)
                    continue
            
            # ⚡ ИСПРАВЛЕНИЕ: Задержка только если состояние НЕ изменилось
            delay = 1.0  # По умолчанию
            if current_state == TradingState.SCANNING:
                delay = 5.0  # Сканирование каждые 5 секунд
            elif current_state == TradingState.SIGNAL_WAIT:
                delay = 2.0  # Ожидание сигналов каждые 2 секунды
            elif current_state == TradingState.MANAGING:
                delay = 1.0  # Управление позициями каждую секунду
            else:
                delay = 0.5  # Для остальных состояний
            
            # Interruptible sleep
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=delay)
                logger.info("Stop event received, exiting main loop")
                break
            except asyncio.TimeoutError:
                pass
                
        except KeyboardInterrupt:
            logger.info("Main loop interrupted (KeyboardInterrupt)")
            await self.stop()
            break
        except Exception as e:
            # Error handling ...
```

## Преимущества исправления

1. **Быстрые переходы**: Состояния SCANNING → LEVEL_BUILDING → SIGNAL_WAIT → SIZING обрабатываются немедленно без ненужных задержек

2. **Правильная логика**: Задержка применяется только когда нужно **ждать** (например, следующего сканирования), а не после каждого перехода

3. **Динамичность**: Бот быстро реагирует на изменения состояния и обрабатывает весь пайплайн за секунды, а не минуты

4. **Оптимизация**: Минимизированы ненужные паузы, что улучшает время реакции на рыночные условия

## Дополнительные улучшения

### В trading_orchestrator.py

Добавить логирование переходов состояний:

```python
async def _execute_scanning_cycle(self, exchange_client) -> None:
    """Выполнить цикл сканирования рынков."""
    # ...
    if scan_results:
        self.enhanced_logger.info(
            f"Scan complete: {len(scan_results)} candidates found, transitioning to LEVEL_BUILDING",
            context
        )
        await self.state_machine.transition_to(
            TradingState.LEVEL_BUILDING,
            f"Found {len(scan_results)} candidates"
        )
    # ...
```

### В scanning_manager.py

Улучшить логирование прогресса:

```python
async def scan_markets(self, exchange_client, session_id: str) -> List[ScanResult]:
    # ...
    logger.info(f"Scanning {len(symbols_to_scan)} symbols...")
    
    # Progress logging
    for i, symbol in enumerate(symbols_to_scan):
        if i % 10 == 0:
            logger.debug(f"Scanning progress: {i}/{len(symbols_to_scan)}")
    # ...
```

## Тестирование

После применения исправления:

1. Запустить бота: `./start.sh`
2. Наблюдать логи: `tail -f logs/general.log`
3. Проверить переходы состояний: должны происходить быстро (< 1 секунды между переходами)
4. Убедиться, что генерация сигналов происходит после сканирования

Ожидаемый лог-последовательность:
```
[SCANNING] Starting market scan...
[SCANNING] Scan complete: 50 candidates found
[LEVEL_BUILDING] Executing level building cycle...
[SIGNAL_WAIT] Executing signal wait cycle...
[SIGNAL_WAIT] Generating signals from 50 scan results...
[SIZING] Executing sizing cycle...
[SIZING] Evaluating 3 signals for risk...
```
