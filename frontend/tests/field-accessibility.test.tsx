import {render,screen} from '@testing-library/react';
import {describe,expect,it} from 'vitest';
import {Field} from '../src/components/BusinessUI';
import {NativeSelect} from '../src/components/ui/native-select';

describe('field labels',()=>{
  it('keeps select labels independent of option text for keyboard and browser automation',()=>{
    render(<Field label="患者"><NativeSelect><option>请选择患者</option><option>虚构患者甲</option></NativeSelect></Field>);
    expect(screen.getByRole('combobox',{name:'患者'})).toBe(screen.getByLabelText('患者',{exact:true}));
  });
});
