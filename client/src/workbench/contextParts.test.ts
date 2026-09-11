import { describe, expect, it } from 'vitest'
import { splitContextText } from './contextParts.ts'

describe('splitContextText', () => {
  it('keeps latex linebreaks in prose and peels a citations line', () => {
    expect(
      splitContextText(
        '\\section{Formative Study}\n\\label{sec:formative-study}\n\n\\subsection{Motivation}\nWe conducted a formative study.\nCitations: smith2020 | Refs: fig:ui',
      ),
    ).toEqual({
      prose: '\\section{Formative Study}\n\\label{sec:formative-study}\n\n\\subsection{Motivation}\nWe conducted a formative study.',
      extras: 'Citations: smith2020 | Refs: fig:ui',
    })
  })

  it('does not treat a mid-prose newline as extras', () => {
    expect(splitContextText('\\section{A}\n\\label{b}')).toEqual({
      prose: '\\section{A}\n\\label{b}',
      extras: '',
    })
  })
})
