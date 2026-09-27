import { HeadContent, Scripts, createRootRoute } from '@tanstack/react-router'

import appCss from '../styles.css?url'

export const Route = createRootRoute({
  head: () => ({
    meta: [
      { charSet: 'utf-8' },
      { name: 'viewport', content: 'width=device-width, initial-scale=1' },
      { title: 'Quant v1' },
      {
        name: 'description',
        content: 'Stock data collection and monitoring dashboard.',
      },
    ],
    links: [
      { rel: 'stylesheet', href: appCss },
      {
        rel: 'icon',
        href:
          'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="12" fill="%2317201b"/><path d="M14 43h36v5H14zM18 36h6v7h-6zM29 26h6v17h-6zM40 16h6v27h-6z" fill="%23d6ff63"/></svg>',
      },
    ],
  }),
  shellComponent: RootDocument,
})

function RootDocument({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <HeadContent />
      </head>
      <body>
        {children}
        <Scripts />
      </body>
    </html>
  )
}
