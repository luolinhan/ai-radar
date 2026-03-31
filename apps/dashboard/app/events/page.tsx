'use client'

import { useState, useEffect } from 'react'

interface Event {
  event_id: string
  source: string
  entity_id: string
  title: string | null
  content_zh: string | null
  url: string
  published_at: string
  alert_level: string
}

export default function EventsPage() {
  const [events, setEvents] = useState<Event[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // 从API获取事件
    fetchEvents()
  }, [])

  const fetchEvents = async () => {
    try {
      const apiUrl = `${window.location.origin}/api`
      const res = await fetch(`${apiUrl}/events`)
      const data = await res.json()
      setEvents(data.items || [])
    } catch (error) {
      console.error('获取事件失败:', error)
      setEvents([])
    }
    setLoading(false)
  }

  const getAlertColor = (level: string) => {
    const colors = {
      S: '#ff4d4f',
      A: '#faad14',
      B: '#1890ff',
      C: '#8c8c8c',
    }
    return colors[level as keyof typeof colors] || '#8c8c8c'
  }

  return (
    <main style={{
      minHeight: '100vh',
      background: '#f5f5f5',
      padding: '2rem'
    }}>
      <div style={{
        maxWidth: '1200px',
        margin: '0 auto'
      }}>
        <h1 style={{
          fontSize: '1.5rem',
          fontWeight: 'bold',
          marginBottom: '1.5rem'
        }}>
          事件列表
        </h1>

        {loading ? (
          <div style={{ textAlign: 'center', padding: '2rem' }}>
            加载中...
          </div>
        ) : events.length === 0 ? (
          <div style={{
            background: 'white',
            padding: '2rem',
            borderRadius: '8px',
            textAlign: 'center'
          }}>
            暂无事件数据
          </div>
        ) : (
          <div style={{ display: 'grid', gap: '1rem' }}>
            {events.map((event) => (
              <div key={event.event_id}
                style={{
                  background: 'white',
                  borderRadius: '8px',
                  padding: '1.5rem',
                  boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
                  borderLeft: `4px solid ${getAlertColor(event.alert_level)}`
                }}
              >
                <div style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  marginBottom: '0.5rem'
                }}>
                  <span style={{
                    fontSize: '0.875rem',
                    color: '#666'
                  }}>
                    {event.source} · {event.entity_id}
                  </span>
                  <span style={{
                    background: getAlertColor(event.alert_level),
                    color: 'white',
                    padding: '0.25rem 0.5rem',
                    borderRadius: '4px',
                    fontSize: '0.75rem'
                  }}>
                    {event.alert_level}
                  </span>
                </div>

                <h3 style={{
                  fontSize: '1rem',
                  fontWeight: '600',
                  marginBottom: '0.5rem'
                }}>
                  {event.title || '无标题'}
                </h3>

                <p style={{
                  color: '#333',
                  fontSize: '0.875rem',
                  lineHeight: '1.6',
                  marginBottom: '1rem'
                }}>
                  {event.content_zh || '暂无中文翻译'}
                </p>

                <div style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center'
                }}>
                  <span style={{
                    fontSize: '0.75rem',
                    color: '#999'
                  }}>
                    {new Date(event.published_at).toLocaleString('zh-CN')}
                  </span>
                  <a href={event.url}
                    target="_blank"
                    style={{
                      color: '#1890ff',
                      fontSize: '0.875rem'
                    }}
                  >
                    查看原文
                  </a>
                </div>
              </div>
            ))}
          </div>
        )}

        <div style={{ marginTop: '2rem' }}>
          <a href="/"
            style={{
              color: '#1890ff',
              textDecoration: 'underline'
            }}
          >
            返回首页
          </a>
        </div>
      </div>
    </main>
  )
}
