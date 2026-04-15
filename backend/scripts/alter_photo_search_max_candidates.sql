-- 若已有库缺列，执行一次（MySQL）
ALTER TABLE photo_search_tasks
  ADD COLUMN max_candidates SMALLINT NOT NULL DEFAULT 4
  COMMENT '单次拍照购最多入库的拼多多候选条数';
