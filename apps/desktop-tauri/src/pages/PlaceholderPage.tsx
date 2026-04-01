interface PlaceholderPageProps {
  title: string;
  description: string;
}

export function PlaceholderPage({ title, description }: PlaceholderPageProps): JSX.Element {
  return (
    <section>
      <h2>{title}</h2>
      <p>{description}</p>
    </section>
  );
}
