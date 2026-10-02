// CommonJS on purpose. As `postcss.config.mjs` this file is loaded through
// Node's ESM loader, which cannot resolve absolute Windows paths during the
// Next.js build (ERR_UNSUPPORTED_ESM_URL_SCHEME: protocol 'c:').
module.exports = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};