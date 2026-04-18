-- MySQL: 选品状态增加 erp_synced（已同步ERP）
-- 在部署后端前执行一次；若库中已有其它自定义值请先备份。

ALTER TABLE products
  MODIFY COLUMN status ENUM('pending','selected','abandoned','erp_synced')
  NOT NULL DEFAULT 'pending';
