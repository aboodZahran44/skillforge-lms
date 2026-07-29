import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '10s', target: 10 },
    { duration: '20s', target: 10 },
    { duration: '5s', target: 0 },
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'],
    http_req_failed: ['rate<0.01'],
  },
};

const BASE_URL = 'http://host.docker.internal:8000';

export default function () {
  const healthRes = http.get(`${BASE_URL}/healthz/`);
  check(healthRes, {
    'health check status is 200': (r) => r.status === 200,
  });

  const searchRes = http.get(`${BASE_URL}/api/courses/search?q=python`);
  check(searchRes, {
    'search status is 200': (r) => r.status === 200,
  });

  sleep(1);
}