import type {ReactNode} from 'react';
import Link from '@docusaurus/Link';
import useBaseUrl from '@docusaurus/useBaseUrl';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import Layout from '@theme/Layout';
import HomepageFeatures from '@site/src/components/HomepageFeatures';
import Heading from '@theme/Heading';

import styles from './index.module.css';

function HomepageHeader() {
  const {siteConfig} = useDocusaurusContext();
  const logo = useBaseUrl('/img/logo.svg');
  const workbench = useBaseUrl('/img/workbench.png');
  return (
    <header className={styles.heroBanner}>
      <div className="container">
        <img className={styles.logo} src={logo} alt="" width={72} height={72} />
        <Heading as="h1" className={styles.title}>
          {siteConfig.title}
        </Heading>
        <p className={styles.subtitle}>{siteConfig.tagline}</p>
        <div className={styles.buttons}>
          <Link className="button button--primary button--lg" to="/docs/intro">
            Get Started
          </Link>
          <Link
            className="button button--secondary button--lg"
            href="https://github.com/zhangyu94/ReviewDistill">
            GitHub
          </Link>
        </div>
        <img
          className={styles.heroImage}
          src={workbench}
          alt="ReviewDistill workbench with a label taxonomy and comments from a paper"
        />
      </div>
    </header>
  );
}

export default function Home(): ReactNode {
  return (
    <Layout
      title="Home"
      description="Distill the comments you write in a LaTeX paper into a reusable agent skill to save your proofreading time.">
      <HomepageHeader />
      <main>
        <HomepageFeatures />
      </main>
    </Layout>
  );
}
