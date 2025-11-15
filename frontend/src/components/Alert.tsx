interface AlertProps {
  type: 'error' | 'success'
  message: string
  className?: string
}

export function Alert({ type, message, className = '' }: AlertProps) {
  return (
    <div className={`alert-message ${type} ${className}`}>
      {message}
    </div>
  )
}

