import type {ReactNode} from 'react';
import Heading from '@theme/Heading';
import styles from './styles.module.css';

const steps = [
  {
    n: '1',
    title: 'Comment in the paper',
    body: (
      <pre className={styles.tex}>{`The results demonstrate
that the method is
effective.
\\myremark{Demonstrate is
too strong here.}`}</pre>
    ),
  },
  {
    n: '2',
    title: 'Extract the comments',
    body: (
      <>
        <pre className={styles.tex}>reviewdistill extract</pre>
        <p>
          After <code>reviewdistill init</code> in the paper folder. That
          finds the macros in the <code>.tex</code> file and stores each
          remark with the sentence it sits in. It does not change the paper.
        </p>
      </>
    ),
  },
  {
    n: '3',
    title: 'Label in the UI',
    body: (
      <p>
        Open the workbench with <code>reviewdistill ui</code>. Assign a{' '}
        <strong>leaf</strong> (a label with no children). You can also let an
        LLM suggest labels if you add an API key in Settings.
      </p>
    ),
  },
  {
    n: '4',
    title: 'Export a skill',
    body: (
      <p>
        Click <strong>Export</strong> in the workbench, or run{' '}
        <code>reviewdistill export</code>. Put <code>SKILL.md</code> where
        your coding agent reads skills so it can reuse those checks on the
        next paper.
      </p>
    ),
  },
];

export default function HomepageFeatures(): ReactNode {
  return (
    <section className={styles.features}>
      <div className="container">
        <div className="row">
          {steps.map((step) => (
            <div key={step.n} className="col col--3">
              <div className="padding-horiz--md">
                <p className={styles.num}>{step.n}</p>
                <Heading as="h3">{step.title}</Heading>
                {step.body}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
