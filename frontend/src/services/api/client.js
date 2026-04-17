import axios from "axios";

const BASE_URL = "";
const TOKEN_KEY = "docmind-token";

// Token — persiste en localStorage para sobrevivir recargas
let _token = localStorage.getItem(TOKEN_KEY) || null;

export function setToken(token) {
  _token = token;
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  _token = null;
  localStorage.removeItem(TOKEN_KEY);
}

export function getToken() {
  return _token;
}

const client = axios.create({
  baseURL: BASE_URL,
  headers: { "Content-Type": "application/json" },
});

// Agregar token a cada request
client.interceptors.request.use((config) => {
  if (_token) {
    config.headers.Authorization = `Bearer ${_token}`;
  }
  return config;
});

// Si 401 → limpiar token y redirigir a login
client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      clearToken();
      window.location.href = "/login";
    }
    return Promise.reject(error);
  },
);

export default client;
