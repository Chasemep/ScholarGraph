import React from 'react'
import katex from 'katex'
import 'katex/dist/katex.min.css'

/**
 * Safely render a LaTeX math expression to HTML using KaTeX.
 */
function renderKatexToHtml(latexStr, displayMode = false) {
  try {
    return katex.renderToString(latexStr.trim(), {
      displayMode,
      throwOnError: false,
      strict: false,
      trust: true,
    })
  } catch {
    return latexStr
  }
}

/**
 * Normalize bare LaTeX tokens (e.g., \frac{...}{...}, \dot{x}, \mathbb{R}^3, x_i)
 * that may appear outside $...$ delimiters in extracted PDF snippets or LLM outputs.
 */
function wrapBareLatexExpressions(text) {
  if (!text) return ''

  // Split by existing math delimiters so we only inspect non-delimited segments
  const mathSplitRegex = /(\$\$[\s\S]+?\$\$|\\\[[\s\S]+?\\\]|\$[^$\n]+?\$|\\\([\s\S]+?\\\))/g
  const segments = text.split(mathSplitRegex)

  const braceGroup = '(?:\\{(?:[^{}]|\\{[^{}]*\\})*\\})'
  const bareCmdPattern = new RegExp(
    `(\\\\(?:frac|dfrac|tfrac)${braceGroup}${braceGroup}(?:\\^[0-9a-zA-Z]+|_[0-9a-zA-Z]+)*|` +
      `\\\\(?:sqrt|dot|ddot|hat|bar|tilde|vec|mathbb|mathcal|mathrm|mathbf|operatorname)${braceGroup}(?:\\^[0-9a-zA-Z]+|_[0-9a-zA-Z]+)*|` +
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
 * Render inline bold (**...**), code (`...`), and markdown bullet prefixes (*   or - )
 * within a plain text fragment.
 */
function renderFormattedPlainSegment(text, keyPrefix) {
  if (!text) return null

  // Replace markdown list prefixes at line starts (e.g. "\n*   " or "^*   ") with a clean bullet
  const cleanedBullets = text.replace(/(^|\n)[ \t]*[*-][ \t]{1,6}/g, '$1  • ')

  const tokenRegex = /(\*\*[^*]+\*\*|`[^`]+`)/g
  const parts = cleanedBullets.split(tokenRegex)

  return parts.map((part, idx) => {
    if (part.startsWith('**') && part.endsWith('**') && part.length > 4) {
      return (
        <strong key={`${keyPrefix}-b-${idx}`} className="font-semibold text-white">
          {part.slice(2, -2)}
        </strong>
      )
    }
    if (part.startsWith('`') && part.endsWith('`') && part.length > 2) {
      return (
        <code
          key={`${keyPrefix}-c-${idx}`}
          className="px-1.5 py-0.5 rounded bg-slate-900/90 text-sky-300 font-mono text-xs border border-slate-700/70"
        >
          {part.slice(1, -1)}
        </code>
      )
    }
    return <React.Fragment key={`${keyPrefix}-t-${idx}`}>{part}</React.Fragment>
  })
}

/**
 * Render a text segment containing LaTeX ($...$, $$...$$, \(...\), \[...\]),
 * bare math expressions, bold text, and bullet points into React elements.
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
          className="block my-2 py-1.5 px-3 rounded-lg bg-slate-900/60 border border-slate-700/60 overflow-x-auto text-center text-slate-100"
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
          className="inline-block mx-0.5 text-slate-100 align-baseline"
          dangerouslySetInnerHTML={{ __html: html }}
        />
      )
    }

    return renderFormattedPlainSegment(token, `${keyPrefix}-p-${idx}`)
  })
}
