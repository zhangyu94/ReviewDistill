import type {ReactNode} from 'react';
import clsx from 'clsx';
import Heading from '@theme/Heading';
import styles from './styles.module.css';

type FeatureItem = {
  title: string;
  description: ReactNode;
};

const FeatureList: FeatureItem[] = [
  {
    title: 'Proofread in the paper',
    description: (
      <>
        Keep using LaTeX comment commands. ReviewDistill extracts them and the
        nearby manuscript so you never maintain a parallel review file.
      </>
    ),
  },
  {
    title: 'Code in the workbench',
    description: (
      <>
        Groups, entries, and an inspector. Optional LLM suggestions; you accept,
        change, or reject. History undoes a bad code.
      </>
    ),
  },
  {
    title: 'Export skills for agents',
    description: (
      <>
        The taxonomy is local SQLite that grows across papers. Export Markdown,
        YAML, or JSON and point a coding agent at the rubric.
      </>
    ),
  },
];

function Feature({title, description}: FeatureItem) {
  return (
    <div className={clsx('col col--4')}>
      <div className="padding-horiz--md">
        <Heading as="h3">{title}</Heading>
        <p>{description}</p>
      </div>
    </div>
  );
}

export default function HomepageFeatures(): ReactNode {
  return (
    <section className={styles.features}>
      <div className="container">
        <div className="row">
          {FeatureList.map((props, idx) => (
            <Feature key={idx} {...props} />
          ))}
        </div>
      </div>
    </section>
  );
}
