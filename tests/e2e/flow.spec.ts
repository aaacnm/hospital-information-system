import {test,expect,type Page} from '@playwright/test';
async function login(page:Page,username:string){
 await page.goto('/login');await page.getByLabel('用户名').fill(username);await page.getByLabel('密码').fill('Demo123!');
 await page.getByRole('button',{name:'登录工作台'}).click();await expect(page.getByRole('button',{name:'退出登录'})).toBeVisible();
}
async function logout(page:Page){await page.getByRole('button',{name:'退出登录'}).click();}
test('ordinary initialization supports a complete outpatient flow without memorized IDs',async({page})=>{
 await login(page,'cashier.demo');await page.goto('/registrations');
 await page.getByLabel('患者',{exact:true}).selectOption({label:'演示患者甲 · DEMO-001'});
 await page.getByLabel('医生与时段').selectOption({index:1});await page.getByRole('button',{name:'确认挂号'}).click();
 await expect(page.getByText('挂号成功',{exact:true})).toBeVisible();await logout(page);
 await login(page,'doctor.demo');await page.goto('/registrations');await page.getByRole('link',{name:'接诊开方'}).click();
 await page.getByLabel('药品 1',{exact:true}).selectOption({index:1});await page.getByLabel('数量 1',{exact:true}).fill('2');
 await page.getByRole('button',{name:'填入教学示例'}).click();await page.getByRole('button',{name:'保存诊疗记录'}).click();
 await page.getByRole('button',{name:'添加药品'}).click();await page.getByLabel('药品 2',{exact:true}).selectOption({index:2});
 await page.getByRole('button',{name:'创建草稿并划价'}).click();await expect(page.getByText('应付金额 ¥ 28.00')).toBeVisible();
 await page.getByRole('button',{name:'提交为待收费'}).first().click();await expect(page.getByText('待收费',{exact:true}).first()).toBeVisible();await logout(page);
 await login(page,'cashier.demo');await page.goto('/billing');await page.getByRole('button',{name:'核对明细'}).click();
 await page.getByRole('button',{name:'确认收费'}).click();await expect(page.getByText('收费成功',{exact:true})).toBeVisible();await logout(page);
 await login(page,'pharmacist.demo');await page.goto('/dispensing');await page.getByRole('button',{name:'核对明细'}).click();
 await page.getByRole('button',{name:'确认发药'}).click();await expect(page.getByText('发药成功',{exact:true})).toBeVisible();await logout(page);
 await login(page,'admin.demo');await page.goto('/audit-logs');await page.getByLabel('动作',{exact:true}).selectOption('prescription.dispense');
 await expect(page.getByRole('cell',{name:'prescription.dispense',exact:true})).toBeVisible();
 await page.goto('/reports');await expect(page.getByText('¥28.00',{exact:true}).first()).toBeVisible();
});
