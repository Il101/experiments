/**
 * Переиспользуемый компонент таблицы
 */

import { Table as BootstrapTable, Badge } from 'react-bootstrap';
import { TableSkeleton } from './Skeleton';
import type { TableColumn, TableProps } from '../../types';

export const Table = <T extends Record<string, any>>({
  data,
  columns,
  loading = false,
  emptyMessage = 'No data available',
  onRowClick,
  className = '',
}: TableProps<T>) => {
  const renderCell = (column: TableColumn<T>, item: T) => {
    const value = typeof column.key === 'string' && column.key.includes('.') 
      ? column.key.split('.').reduce((obj: any, key: string) => obj?.[key], item)
      : item[column.key as keyof T];

    if (column.render) {
      return column.render(value, item);
    }

    // Default rendering based on value type
    if (typeof value === 'boolean') {
      return (
        <Badge bg={value ? 'success' : 'secondary'}>
          {value ? 'Yes' : 'No'}
        </Badge>
      );
    }

    if (typeof value === 'number') {
      return value.toLocaleString();
    }

    return value?.toString() || '-';
  };

  const renderLoadingState = () => {
    // Используем TableSkeleton вместо спиннера
    return <TableSkeleton rows={5} columns={columns.length} />;
  };

  const renderEmptyRow = () => (
    <tr>
      <td colSpan={columns.length} className="text-center py-4 text-muted">
        {emptyMessage}
      </td>
    </tr>
  );

  // Если загрузка - показываем skeleton без Bootstrap Table
  if (loading) {
    return (
      <div className={`table-responsive ${className}`}>
        {renderLoadingState()}
      </div>
    );
  }

  return (
    <div className="table-responsive">
      <BootstrapTable hover className={`mb-0 ${className}`}>
        <thead className="table-light">
          <tr>
            {columns.map((column, index) => (
              <th
                key={index}
                style={{ width: column.width }}
                className={column.sortable ? 'cursor-pointer' : ''}
              >
                {column.title}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.length === 0 ? (
            renderEmptyRow()
          ) : (
            data.map((item, rowIndex) => (
              <tr
                key={rowIndex}
                onClick={() => onRowClick?.(item)}
                className={onRowClick ? 'cursor-pointer' : ''}
              >
                {columns.map((column, colIndex) => (
                  <td key={colIndex}>
                    {renderCell(column, item)}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </BootstrapTable>
    </div>
  );
};


