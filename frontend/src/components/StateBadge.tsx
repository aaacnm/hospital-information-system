import {Badge} from './ui/badge';

const tones: Record<string, string> = {
  已退费: 'state-refund',
  候诊: 'state-waiting',
  就诊中: 'state-active',
  草稿: 'state-draft',
  待收费: 'state-pending',
  已收费: 'state-paid',
  已发药: 'state-done',
  已完成: 'state-done',
  已取消: 'state-muted',
  启用: 'state-done',
  禁用: 'state-muted',
};

export function StateBadge({value}: {value: string}) {
  return (
    <Badge variant="outline" className={'state-badge ' + (tones[value] || 'state-muted')}>
      <span className="size-1.5 rounded-full bg-current opacity-70"/>
      {value}
    </Badge>
  );
}
