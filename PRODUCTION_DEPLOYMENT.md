# Breakout Bot Production Deployment Guide

## Overview

This guide covers the production deployment of the Breakout Bot Trading System using Docker containers and modern DevOps practices.

## Prerequisites

- Docker and Docker Compose installed
- At least 4GB RAM available
- 20GB free disk space
- Linux/macOS/Windows with WSL2

## Quick Start

1. **Clone and configure:**
   ```bash
   git clone <repository-url>
   cd breakout-bot
   cp env.example .env
   # Edit .env with your configuration
   ```

2. **Deploy:**
   ```bash
   ./deploy.sh
   ```

3. **Access the system:**
   - Frontend: http://localhost:3000
   - API: http://localhost:8000
   - API Docs: http://localhost:8000/api/docs
   - Grafana: http://localhost:3001 (admin/admin)
   - Prometheus: http://localhost:9090

## Architecture

### Services

- **breakout-bot-api**: Main trading engine and API
- **breakout-bot-frontend**: React web interface
- **redis**: Caching and session storage
- **prometheus**: Metrics collection
- **grafana**: Monitoring dashboards

### Data Persistence

- **SQLite Database**: Trading data, positions, performance metrics
- **Logs**: System logs and trading activity
- **Reports**: Performance reports and analytics

## Configuration

### Environment Variables

Key configuration options in `.env`:

```bash
# Trading Mode
TRADING_MODE=paper  # or 'live'

# Exchange Configuration
EXCHANGE_NAME=binance
EXCHANGE_API_KEY=your_key
EXCHANGE_SECRET_KEY=your_secret

# Risk Management
MAX_DAILY_LOSS_PERCENT=5.0
MAX_POSITION_SIZE_PERCENT=2.0
```

### Security

1. **API Keys**: Store exchange API keys securely
2. **Secrets**: Use strong, unique secret keys
3. **Network**: Configure firewall rules
4. **SSL**: Use reverse proxy with SSL in production

## Monitoring

### Health Checks

- API: `GET /api/health`
- Frontend: `GET /`
- Database: Automatic connection monitoring

### Metrics

- Trading performance metrics
- System resource usage
- Error rates and response times
- Position and risk metrics

### Alerts

Configure alerts for:
- High drawdown
- System errors
- Resource usage
- Trading anomalies

## Maintenance

### Updates

```bash
# Update to latest version
./update.sh

# Manual update
docker-compose pull
docker-compose up -d
```

### Backups

Automatic backups are created during updates. Manual backup:

```bash
# Create backup
tar -czf backup_$(date +%Y%m%d_%H%M%S).tar.gz data/ logs/

# Restore backup
tar -xzf backup_YYYYMMDD_HHMMSS.tar.gz
```

### Logs

```bash
# View all logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f breakout-bot-api
docker-compose logs -f breakout-bot-frontend
```

## Troubleshooting

### Common Issues

1. **API not responding:**
   ```bash
   docker-compose restart breakout-bot-api
   docker-compose logs breakout-bot-api
   ```

2. **Database issues:**
   ```bash
   # Check database file permissions
   ls -la data/
   # Restore from backup if needed
   ```

3. **Memory issues:**
   ```bash
   # Check resource usage
   docker stats
   # Increase memory limits in docker-compose.yml
   ```

### Performance Optimization

1. **Resource Limits**: Adjust in `docker-compose.yml`
2. **Database**: Consider PostgreSQL for high-volume trading
3. **Caching**: Configure Redis for better performance
4. **Monitoring**: Set up proper alerting thresholds

## Security Considerations

### Production Checklist

- [ ] Change default passwords
- [ ] Configure SSL/TLS
- [ ] Set up firewall rules
- [ ] Enable audit logging
- [ ] Configure backup encryption
- [ ] Set up monitoring alerts
- [ ] Test disaster recovery

### API Security

- Use API keys for authentication
- Implement rate limiting
- Validate all inputs
- Log all trading activities

## Scaling

### Horizontal Scaling

- Multiple API instances behind load balancer
- Separate database server
- Redis cluster for caching
- CDN for frontend assets

### Vertical Scaling

- Increase container resources
- Use faster storage (SSD)
- Optimize database queries
- Implement connection pooling

## Disaster Recovery

### Backup Strategy

1. **Database**: Daily automated backups
2. **Configuration**: Version controlled
3. **Logs**: Rotated and archived
4. **Code**: Git repository with tags

### Recovery Procedures

1. **Service Recovery**: `./deploy.sh`
2. **Data Recovery**: Restore from backup
3. **Configuration Recovery**: Git checkout
4. **Full Recovery**: Complete redeployment

## Support

### Logs and Debugging

- Check container logs: `docker-compose logs`
- Monitor resource usage: `docker stats`
- Review application logs: `tail -f logs/breakout_bot.log`

### Performance Monitoring

- Grafana dashboards for system metrics
- Prometheus for detailed metrics
- Application-specific monitoring

## License

This software is provided under the MIT License. See LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## Changelog

See CHANGELOG.md for version history and updates.
