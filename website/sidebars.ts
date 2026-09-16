import type {SidebarsConfig} from '@docusaurus/plugin-content-docs';

const sidebars: SidebarsConfig = {
  docsSidebar: [
    {
      type: 'category',
      label: 'Guide',
      collapsed: false,
      items: ['intro', 'install', 'first-paper', 'labeling', 'export'],
    },
    {
      type: 'category',
      label: 'Reference',
      items: ['cli', 'workbench', 'extract', 'llm', 'history', 'data', 'internals'],
    },
  ],
};

export default sidebars;
