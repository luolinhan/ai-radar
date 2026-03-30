export default function HomePage() {
  return (
    <main style={{
      minHeight: '100vh',
      background: '#f5f5f5',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      padding: '2rem'
    }}>
      <h1 style={{
        fontSize: '2rem',
        fontWeight: 'bold',
        marginBottom: '1rem'
      }}>
        AI Radar
      </h1>
      <p style={{ color: '#666', marginBottom: '2rem' }}>
        全球AI情报监控系统
      </p>

      <div style={{
        background: 'white',
        borderRadius: '8px',
        padding: '2rem',
        boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
        maxWidth: '800px',
        width: '100%'
      }}>
        <h2 style={{ fontSize: '1.25rem', marginBottom: '1rem' }}>
          系统状态
        </h2>
        <div style={{ display: 'grid', gap: '1rem' }}>
          <div style={{
            padding: '1rem',
            background: '#f0f0f0',
            borderRadius: '4px',
            display: 'flex',
            justifyContent: 'space-between'
          }}>
            <span>API服务</span>
            <span style={{ color: '#52c41a' }}>运行中</span>
          </div>
          <div style={{
            padding: '1rem',
            background: '#f0f0f0',
            borderRadius: '4px',
            display: 'flex',
            justifyContent: 'space-between'
          }}>
            <span>采集器</span>
            <span style={{ color: '#52c41a' }}>运行中</span>
          </div>
          <div style={{
            padding: '1rem',
            background: '#f0f0f0',
            borderRadius: '4px',
            display: 'flex',
            justifyContent: 'space-between'
          }}>
            <span>翻译器</span>
            <span style={{ color: '#52c41a' }}>运行中</span>
          </div>
        </div>

        <h2 style={{ fontSize: '1.25rem', marginTop: '2rem', marginBottom: '1rem' }}>
          功能模块
        </h2>
        <ul style={{ lineHeight: '2' }}>
          <li>多源采集: RSS、GitHub、X/Twitter、arXiv</li>
          <li>中文翻译: 自动翻译英文源内容</li>
          <li>影响分析: 判断对研究、产品、市场的影响</li>
          <li>飞书通知: S/A级事件即时推送</li>
        </ul>

        <div style={{ marginTop: '2rem' }}>
          <a href="/events"
            style={{
              display: 'inline-block',
              padding: '0.75rem 1.5rem',
              background: '#1890ff',
              color: 'white',
              borderRadius: '4px',
              textDecoration: 'none'
            }}
          >
            查看事件列表
          </a>
        </div>
      </div>
    </main>
  )
}