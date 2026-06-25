// markdown-it + highlight.js 渲染 Claude 回复
// 安全策略：HTML 转义默认开启（html: false）+ linkify + 代码高亮
import MarkdownIt from 'markdown-it'
import hljs from 'highlight.js'

const md = new MarkdownIt({
  html: false,        // 不允许原始 HTML 注入（XSS 防护）
  breaks: true,       // 单换行 → <br>（聊天场景更自然）
  linkify: true,      // 自动识别链接
  typographer: true,
  highlight(str: string, lang: string): string {
    if (lang && hljs.getLanguage(lang)) {
      try {
        const highlighted = hljs.highlight(str, { language: lang, ignoreIllegals: true }).value
        return `<pre class="code-block"><code class="hljs language-${lang}">${highlighted}</code></pre>`
      } catch {
        /* fall through */
      }
    }
    return `<pre class="code-block"><code class="hljs">${md.utils.escapeHtml(str)}</code></pre>`
  },
})

// 链接强制 target=_blank + rel=noopener
const defaultLinkOpen = md.renderer.rules.link_open || function (tokens, idx, options, _env, self) {
  return self.renderToken(tokens, idx, options)
}
md.renderer.rules.link_open = function (tokens, idx, options, env, self) {
  const aIndex = tokens[idx].attrIndex('target')
  if (aIndex < 0) {
    tokens[idx].attrPush(['target', '_blank'])
    tokens[idx].attrPush(['rel', 'noopener noreferrer'])
  } else {
    tokens[idx].attrs![aIndex][1] = '_blank'
  }
  return defaultLinkOpen(tokens, idx, options, env, self)
}

export function renderMarkdown(text: string): string {
  if (!text) return ''
  return md.render(text)
}
