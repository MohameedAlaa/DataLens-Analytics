import test from 'node:test';
import assert from 'node:assert/strict';
import { extractErrorMessage } from './apiClient.js';

test('apiClient.extractErrorMessage handles Pydantic validation error arrays', () => {
  const err = {
    response: {
      status: 422,
      data: {
        detail: [
          { loc: ['body', 'question'], msg: 'Field required' },
          { loc: ['body', 'dataset_id'], msg: 'Invalid UUID format' }
        ]
      }
    }
  };

  const msg = extractErrorMessage(err);
  assert.equal(msg, 'Field required (body.question); Invalid UUID format (body.dataset_id)');
});

test('apiClient.extractErrorMessage handles string detail', () => {
  const err = {
    response: {
      status: 404,
      data: {
        detail: 'Dataset f8cb8777 not found in catalog'
      }
    }
  };

  const msg = extractErrorMessage(err);
  assert.equal(msg, 'Dataset f8cb8777 not found in catalog');
});

test('apiClient.extractErrorMessage handles object detail safely without crashing React', () => {
  const err = {
    response: {
      status: 400,
      data: {
        detail: { code: 'INVALID_HEADER', reason: 'Missing column names' }
      }
    }
  };

  const msg = extractErrorMessage(err);
  assert.equal(typeof msg, 'string');
  assert.ok(msg.includes('INVALID_HEADER'));
});

test('apiClient.extractErrorMessage intercepts HTML 502/504 Bad Gateway pages', () => {
  const err = {
    response: {
      status: 502,
      data: '<!DOCTYPE html><html><head><title>502 Bad Gateway</title></head><body>nginx</body></html>'
    }
  };

  const msg = extractErrorMessage(err);
  assert.equal(msg, 'Server error (502): Service temporarily unavailable.');
});

test('apiClient.extractErrorMessage handles Network Error', () => {
  const err = new Error('Network Error');
  const msg = extractErrorMessage(err);
  assert.equal(msg, 'Network error: Please check your connection to the server.');
});

test('apiClient.extractErrorMessage handles timeout error', () => {
  const err = {
    code: 'ECONNABORTED',
    message: 'timeout of 30000ms exceeded'
  };
  const msg = extractErrorMessage(err);
  assert.equal(msg, 'Request timed out. Please try again.');
});

test('apiClient.extractErrorMessage handles cancellation errors', () => {
  const err = { name: 'AbortError', message: 'The user aborted a request.' };
  const msg = extractErrorMessage(err);
  assert.equal(msg, 'Request was cancelled');
});
