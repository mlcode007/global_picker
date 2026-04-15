-- 若已有库缺列，执行一次（MySQL）
ALTER TABLE photo_search_tasks
  ADD COLUMN fetch_pdd_links TINYINT(1) NOT NULL DEFAULT 1
  COMMENT '是否进入拼多多详情解析商品链接';
