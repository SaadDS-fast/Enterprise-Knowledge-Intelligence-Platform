export default function ConfidenceIndicator({ value }: { value: string | null | undefined }) {
  const label = value ? value.replaceAll("_", " ") : "none";
  return (
    <span className="confidence" aria-label={`Confidence ${label}`}>
      <span aria-hidden="true" />
      {label}
    </span>
  );
}
