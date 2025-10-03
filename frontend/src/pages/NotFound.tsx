/**
 * Страница 404
 */

import React from 'react';
import { Container, Row, Col } from 'react-bootstrap';
import { Button } from '../components/ui';
import { useNavigate } from 'react-router-dom';

export const NotFound: React.FC = () => {
  const navigate = useNavigate();

  return (
    <Container className="text-center py-5">
      <Row className="justify-content-center">
        <Col md={6}>
          <div className="py-5">
            <h1 className="display-1 text-muted">404</h1>
            <h2 className="h4 mb-3">Page Not Found</h2>
            <p className="text-muted mb-4">
              The page you're looking for doesn't exist or has been moved.
            </p>
            <Button
              variant="primary"
              onClick={() => navigate('/dashboard')}
            >
              Go to Dashboard
            </Button>
          </div>
        </Col>
      </Row>
    </Container>
  );
};


