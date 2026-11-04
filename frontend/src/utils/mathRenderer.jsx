import React from 'react'
import katex from 'katex'
import 'katex/dist/katex.min.css'

/**
 * Safely render a LaTeX math expression to HTML using KaTeX.
 * CRITICAL: output: 'html' prevents KaTeX from emitting both MathML (<math>) and HTML,
 * which caused duplicate symbols (e.g. "i \n i", "v \n i") on copy or in text nodes.
 */
export function renderKatexToHtml(latexStr, displayMode = false) {
  try {
    return katex.renderToString(latexStr.trim(), {
      displayMode,
      throwOnError: false,
      strict: false,
      trust: true,
      output: 'html',
    })
  } catch {
    return latexStr
  }
}

/**
 * Normalize bare LaTeX tokens (e.g., \frac{...}{...}, \dot{x}, \mathbb{R}^3, \|x_i - x_j\|^2, x_i)
 * that may appear outside $...$ delimiters in extracted PDF snippets or LLM outputs.
 */
export function wrapBareLatexExpressions(text) {
  if (!text) return ''

  // Split by existing math delimiters so we only inspect non-delimited segments
  const mathSplitRegex = /(\$\$[\s\S]+?\$\$|\\\[[\s\S]+?\\\]|\$[^$\n]+?\$|\\\([\s\S]+?\\\))/g
  const segments = text.split(mathSplitRegex)

  const braceGroup = '(?:\\{(?:[^{}]|\\{(?:[^{}]|\\{[^{}]*\\})*\\})*\\})'
  const bareCmdPattern = new RegExp(
    `(\\\\(?:frac|dfrac|tfrac)${braceGroup}${braceGroup}(?:\\^${braceGroup}|\\^[0-9a-zA-Z]+|_${braceGroup}|_[0-9a-zA-Z]+)*|` +
      `\\\\(?:sqrt|dot|ddot|hat|bar|tilde|vec|mathbb|mathcal|mathrm|mathbf|operatorname)${braceGroup}(?:\\^${braceGroup}|\\^[0-9a-zA-Z]+|_${braceGroup}|_[0-9a-zA-Z]+)*|` +
      `\\\\\\|[^|\\n]+?\\\\\\|(?:\\^${braceGroup}|\\^[0-9a-zA-Z]+|_${braceGroup}|_[0-9a-zA-Z]+)*|` +
      `\\\\(?:alpha|beta|gamma|delta|epsilon|varepsilon|zeta|eta|theta|iota|kappa|lambda|mu|nu|xi|pi|rho|sigma|tau|upsilon|phi|varphi|chi|psi|omega|Gamma|Delta|Theta|Lambda|Xi|Pi|Sigma|Upsilon|Phi|Psi|Omega|infty|partial|nabla|sum|prod|int|cdot|times|pm|leq|geq|neq|approx|equiv|in|subset|subseteq|forall|exists|rightarrow|leftarrow|Rightarrow|mapsto)\\b(?:\\^${braceGroup}|\\^[0-9a-zA-Z]+|_${braceGroup}|_[0-9a-zA-Z]+)*)`,
    'g'
  )

  return segments
    .map((seg, idx) => {
      // Odd indices are already inside $...$, $$...$$, \(...\), or \[...\]
      if (idx % 2 === 1) return seg

      let updated = seg.replace(bareCmdPattern, '$$$1$$')

      // Wrap bare subscript/superscript variable expressions like x_i, v_j, a_{ij}, d_k, L_x
      // when surrounded by whitespace or punctuation (avoiding paper_id slugs like paper_hu2021)
      updated = updated.replace(
        /(^|[\s(,:;])([a-zA-Z](?:_\{[a-zA-Z0-9,+\-\s]+\}|_[a-zA-Z0-9]|\^\{[a-zA-Z0-9,+\-\s]+\}|\^[0-9a-zA-Z])+)(?=[\s.,;:!?)]|$)/g,
        '$1$$$2$$'
      )

      return updated
    })
    .join('')
}

/**
 * Render inline bold (**...**), italics (*...*), code (`...`), and plain text.
 */
function renderInlineStyles(text, keyPrefix) {
  if (!text) return null

  const tokenRegex = /(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)/g
  const parts = text.split(tokenRegex)

  return parts.map((part, idx) => {
    if (part.startsWith('**') && part.endsWith('**') && part.length > 4) {
      return (
        <strong key={`${keyPrefix}-b-${idx}`} className="font-semibold text-[#f4f4f5]">
          {part.slice(2, -2)}
        </strong>
      )
    }
    if (part.startsWith('*') && part.endsWith('*') && part.length > 2) {
      return (
        <em key={`${keyPrefix}-em-${idx}`} className="italic text-[#d4d4d8]">
          {part.slice(1, -1)}
        </em>
      )
    }
    if (part.startsWith('`') && part.endsWith('`') && part.length > 2) {
      return (
        <code
          key={`${keyPrefix}-c-${idx}`}
          className="px-1.5 py-0.5 rounded bg-[#18181b] text-[#a5b4fc] font-mono text-xs border border-[#27272a]"
        >
          {part.slice(1, -1)}
        </code>
      )
    }
    return <React.Fragment key={`${keyPrefix}-t-${idx}`}>{part}</React.Fragment>
  })
}

/**
 * Render an inline segment containing LaTeX ($...$, $$...$$, \(...\), \[...\])
 * and inline styles (bold, italics, code) into React elements.
 */
export function renderMathSegment(rawText, keyPrefix = 'math') {
  if (!rawText) return null

  const normalized = wrapBareLatexExpressions(rawText)
  const mathRegex = /(\$\$[\s\S]+?\$\$|\\\[[\s\S]+?\\\]|\$[^$\n]+?\$|\\\([\s\S]+?\\\))/g
  const tokens = normalized.split(mathRegex)

  return tokens.map((token, idx) => {
    if (!token) return null

    // Display math: $$...$$ or \[...\]
    if (
      (token.startsWith('$$') && token.endsWith('$$') && token.length > 4) ||
      (token.startsWith('\\[') && token.endsWith('\\]') && token.length > 4)
    ) {
      const inner = token.slice(2, -2)
      const html = renderKatexToHtml(inner, true)
      return (
        <span
          key={`${keyPrefix}-dm-${idx}`}
          className="block my-3 py-2.5 px-4 rounded-xl bg-[#18181b]/95 border border-[#27272a] overflow-x-auto text-center text-[#f4f4f5] shadow-inner"
          dangerouslySetInnerHTML={{ __html: html }}
        />
      )
    }

    // Inline math: $...$ or \(...\)
    if (
      (token.startsWith('$') && token.endsWith('$') && token.length > 2) ||
      (token.startsWith('\\(') && token.endsWith('\\)') && token.length > 4)
    ) {
      const inner = token.startsWith('$') ? token.slice(1, -1) : token.slice(2, -2)
      const html = renderKatexToHtml(inner, false)
      return (
        <span
          key={`${keyPrefix}-im-${idx}`}
          className="inline-block mx-0.5 text-[#f4f4f5] align-baseline"
          dangerouslySetInnerHTML={{ __html: html }}
        />
      )
    }

    return renderInlineStyles(token, `${keyPrefix}-s-${idx}`)
  })
}
