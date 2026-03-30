import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'AI Radar - 全球AI情报监控系统',
  description: '监控全球AI行业重要人物、机构、动态',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="zh">
      <body style={{ fontFamily: 'system-ui, sans-serif', margin: 0 }}>
        {children}
      </body>
    </html>
  )
}