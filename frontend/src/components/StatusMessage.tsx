interface StatusMessageProps {
  tone?: 'info' | 'error' | 'success';
  title: string;
  children?: React.ReactNode;
}

export function StatusMessage({ tone = 'info', title, children }: StatusMessageProps) {
  return <div className={`status-message status-${tone}`} role={tone === 'error' ? 'alert' : 'status'}><strong>{title}</strong>{children ? <p>{children}</p> : null}</div>;
}
