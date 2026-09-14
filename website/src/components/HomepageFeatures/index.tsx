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
    title: 'Group comments',
    description: (
      <>
        Issue taxonomy, comments, and an inspector. Optional LLM suggestions; you accept
        or pick a type. History undoes a bad label.
      </>
    ),
  },
  {
    title: 'Export skills for agents',
    description: (
      <>
        The taxonomy grows across papers. Export Markdown as a review skill,
        or YAML/JSON as a taxonomy dump, and give the skill to a coding agent.
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
