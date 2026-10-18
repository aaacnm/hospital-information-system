import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { ModulePlaceholder } from '../src/components/ModulePlaceholder';

describe('ModulePlaceholder', () => {
  it('states that backend data is pending instead of claiming a business result', () => {
    render(<ModulePlaceholder title="收费台" description="后端重新计算处方金额。" requiredRoles="收费员" endpoint="POST /api/prescriptions/{id}/charge" />);
    expect(screen.getByText('当前页面等待后端服务接入')).toBeInTheDocument();
    expect(screen.getAllByText('POST /api/prescriptions/{id}/charge')).toHaveLength(2);
    expect(screen.queryByText(/收费成功|库存减少|订单已生成/)).not.toBeInTheDocument();
  });
});
