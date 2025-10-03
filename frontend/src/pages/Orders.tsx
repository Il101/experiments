/**
 * Orders Page
 * Dedicated page for viewing and managing orders
 */

import React from 'react';
import { Card, Table, Badge, Spinner } from 'react-bootstrap';
import { useOrders } from '../hooks';

export const Orders: React.FC = () => {
  const { data: orders, isLoading, error } = useOrders();

  if (isLoading) {
    return (
      <div className="text-center py-5">
        <Spinner animation="border" variant="primary" />
        <p className="mt-3 text-muted">Loading orders...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="alert alert-danger">
        <strong>Error loading orders:</strong> {error.message}
      </div>
    );
  }

  const getOrderTypeVariant = (side: string) => {
    return side === 'BUY' ? 'success' : 'danger';
  };

  return (
    <div className="orders-page">
      <div className="d-flex justify-content-between align-items-center mb-4">
        <div>
          <h2>Orders</h2>
          <p className="text-muted mb-0">
            Manage your active and pending orders
          </p>
        </div>
      </div>

      <Card>
        <Card.Body>
          {!orders || orders.length === 0 ? (
            <div className="text-center py-5 text-muted">
              <div className="mb-3" style={{ fontSize: '3rem' }}>📋</div>
              <p>No orders to display</p>
            </div>
          ) : (
            <Table responsive hover>
              <thead>
                <tr>
                  <th>Symbol</th>
                  <th>Type</th>
                  <th>Side</th>
                  <th>Price</th>
                  <th>Quantity</th>
                  <th>Status</th>
                  <th>Time</th>
                </tr>
              </thead>
              <tbody>
                {orders.map((order) => (
                  <tr key={order.id}>
                    <td>
                      <strong>{order.symbol}</strong>
                    </td>
                    <td>{order.type}</td>
                    <td>
                      <Badge bg={getOrderTypeVariant(order.side)}>
                        {order.side}
                      </Badge>
                    </td>
                    <td>${order.price?.toFixed(2) || 'Market'}</td>
                    <td>{order.qty}</td>
                    <td>
                      <Badge bg="warning" text="dark">
                        {order.status}
                      </Badge>
                    </td>
                    <td>
                      <small className="text-muted">
                        {new Date(order.createdAt).toLocaleString()}
                      </small>
                    </td>
                  </tr>
                ))}
              </tbody>
            </Table>
          )}
        </Card.Body>
      </Card>
    </div>
  );
};

export default Orders;
