import type { AgentType } from '../../types/chat';
import { Utensils, CheckSquare, Calendar, Bot } from 'lucide-react';

interface AgentBadgeProps {
  agent: AgentType;
  size?: 'sm' | 'md';
}

const AGENT_CONFIG = {
  food_agent: {
    name: 'Food Agent',
    icon: Utensils,
    color: 'text-orange-400',
    bgColor: 'bg-orange-500/10',
    borderColor: 'border-orange-500/20',
  },
  task_agent: {
    name: 'Task Agent',
    icon: CheckSquare,
    color: 'text-blue-400',
    bgColor: 'bg-blue-500/10',
    borderColor: 'border-blue-500/20',
  },
  event_agent: {
    name: 'Event Agent',
    icon: Calendar,
    color: 'text-purple-400',
    bgColor: 'bg-purple-500/10',
    borderColor: 'border-purple-500/20',
  },
  general: {
    name: 'Assistant',
    icon: Bot,
    color: 'text-text-secondary',
    bgColor: 'bg-bg-hover',
    borderColor: 'border-border',
  },
} as const;

export const AgentBadge: React.FC<AgentBadgeProps> = ({ agent, size = 'sm' }) => {
  const config = AGENT_CONFIG[agent];
  const Icon = config.icon;

  const sizeClasses = size === 'sm'
    ? 'text-xs px-2 py-1 gap-1'
    : 'text-sm px-3 py-1.5 gap-1.5';

  const iconSize = size === 'sm' ? 'w-3 h-3' : 'w-4 h-4';

  return (
    <div
      className={`inline-flex items-center rounded-full border ${sizeClasses}
                 ${config.color} ${config.bgColor} ${config.borderColor}
                 transition-colors`}
    >
      <Icon className={iconSize} />
      <span className="font-medium">{config.name}</span>
    </div>
  );
};
