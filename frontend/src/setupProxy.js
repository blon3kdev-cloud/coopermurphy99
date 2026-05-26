const { createProxyMiddleware } = require('http-proxy-middleware')

/** Same-origin proxy so EventSource /api/bitcoin/stream is not buffered by CRA. */
module.exports = function setupProxy(app) {
  app.use(
    '/api',
    createProxyMiddleware({
      target: 'http://localhost:4000',
      changeOrigin: true,
      onProxyRes(proxyRes, req) {
        if (req.url?.includes('/bitcoin/stream')) {
          proxyRes.headers['cache-control'] = 'no-cache, no-transform'
          proxyRes.headers['x-accel-buffering'] = 'no'
        }
      },
    }),
  )
}
