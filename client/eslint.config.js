import antfu from '@antfu/eslint-config'

export default antfu(
  {
    vue: true,
    typescript: true,
    ignores: [
      '**/dist/**',
      'pnpm-workspace.yaml',
      'pnpm-lock.yaml',
    ],
  },
  {
    rules: {
      'arrow-parens': ['error', 'always'],
      'style/arrow-parens': ['error', 'always'],
      'curly': ['error', 'multi-line'],
      'antfu/if-newline': ['off'],
      'antfu/top-level-function': ['off'],
      'style/max-statements-per-line': 'off',
    },
  },
)
