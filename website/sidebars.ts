import type {SidebarsConfig} from '@docusaurus/plugin-content-docs';

const sidebars: SidebarsConfig = {
  docsSidebar: [
    'intro',
    'install',
    'workflow',
    {
      type: 'category',
      label: 'Using ReviewDistill',
      items: ['ui', 'llm', 'history'],
    },
    'export',
    'cli',
    'internals',
  ],
};

export default sidebars;
