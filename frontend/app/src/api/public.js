import axios from 'axios'

const rawBaseUrl = import.meta.env.VITE_BACKEND_API_URL || '/backend'
const baseURL = rawBaseUrl.endsWith('/') ? rawBaseUrl.slice(0, -1) : rawBaseUrl

const publicApi = axios.create({
  baseURL,
})

export default publicApi
