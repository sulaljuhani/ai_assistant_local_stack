import { useEffect } from 'react';
import { X, AlertCircle, CheckCircle, Info } from 'lucide-react';

export type ToastType = 'success' | 'error' | 'info';

interface ToastProps {
  message: string;
  type: ToastType;
  onClose: () => void;
  duration?: number;
}

const TOAST_CONFIG = {
  success: {
    icon: CheckCircle,
    bgColor: 'bg-accent-green/10',
    borderColor: 'border-accent-green/30',
    iconColor: 'text-accent-green',
  },
  error: {
    icon: AlertCircle,
    bgColor: 'bg-error/10',
    borderColor: 'border-error/30',
    iconColor: 'text-error',
  },
  info: {
    icon: Info,
    bgColor: 'bg-accent-blue/10',
    borderColor: 'border-accent-blue/30',
    iconColor: 'text-accent-blue',
  },
};

export const Toast: React.FC<ToastProps> = ({
  message,
  type,
  onClose,
  duration = 5000,
}) => {
  const config = TOAST_CONFIG[type];
  const Icon = config.icon;

  useEffect(() => {
    if (duration > 0) {
      const timer = setTimeout(onClose, duration);
      return () => clearTimeout(timer);
    }
  }, [duration, onClose]);

  return (
    <div
      className={`fixed bottom-6 right-6 z-50 max-w-md animate-slide-in-right
                 border rounded-lg shadow-lg p-4 ${config.bgColor} ${config.borderColor}
                 backdrop-blur-sm`}
      role="alert"
    >
      <div className="flex items-start gap-3">
        <Icon className={`w-5 h-5 flex-shrink-0 mt-0.5 ${config.iconColor}`} />
        <p className="flex-1 text-sm text-text-primary leading-relaxed">{message}</p>
        <button
          onClick={onClose}
          className="flex-shrink-0 p-1 rounded hover:bg-bg-hover transition-colors"
          aria-label="Close notification"
        >
          <X className="w-4 h-4 text-text-secondary" />
        </button>
      </div>
    </div>
  );
};
