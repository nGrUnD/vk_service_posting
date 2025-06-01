// src/api/axios.js
import axios from 'axios';

const api = axios.create({
    baseURL: 'http://172.18.0.3:8000',
    withCredentials: true,
    headers: { 'Content-Type': 'application/json' },
});


export default api;