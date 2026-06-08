-- MySQL: 商品表增加 first_sku_image 字段（第一个销售属性SKU图，用于1688匹配）
-- 在部署后端前执行一次

ALTER TABLE products
  ADD COLUMN first_sku_image VARCHAR(1024) DEFAULT NULL COMMENT '第一个销售属性SKU图（用于1688匹配）'
  AFTER main_image_url;
