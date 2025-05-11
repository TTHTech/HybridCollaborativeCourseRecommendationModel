import os
import pickle
import logging
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Union, Any

logger = logging.getLogger("recommendation-api")


class RecommenderModel:
    """Model xử lý đề xuất khóa học"""

    def __init__(self, model_path: str):
        """
        Khởi tạo model

        Args:
            model_path: Đường dẫn đến file model
        """
        self.model_path = model_path
        self.model_data = None
        self.model = None
        self.dataset = None
        self.course_features = None
        self.courses_df = None
        self.mine_indices = None
        self.startup_time = datetime.now()

    def load(self) -> bool:
        """
        Tải model từ file

        Returns:
            True nếu tải thành công, False nếu thất bại
        """
        try:
            if not os.path.exists(self.model_path):
                logger.error(f"Không tìm thấy file model: {self.model_path}")
                return False

            logger.info(f"Đang tải model từ {self.model_path}...")
            with open(self.model_path, 'rb') as f:
                self.model_data = pickle.load(f)

            # Lấy các thành phần từ model_data
            self.model = self.model_data.get('model')
            self.dataset = self.model_data.get('dataset')
            self.course_features = self.model_data.get('course_features_matrix')
            self.courses_df = self.model_data.get('courses_df')
            self.mine_indices = self.model_data.get('mine_course_indices')

            # Kiểm tra tất cả các thành phần cần thiết đã được tải
            if self.model is None or self.dataset is None or self.course_features is None:
                logger.error("Model không có đủ các thành phần cần thiết")
                return False

            user_count = len(self.dataset.mapping()[0])
            item_count = len(self.dataset.mapping()[2])
            mine_count = len(self.mine_indices) if self.mine_indices is not None else 0

            logger.info(f"✓ Đã tải model: {user_count} users, {item_count} courses, {mine_count} mine courses")
            return True
        except Exception as e:
            logger.exception(f"Lỗi khi tải model: {str(e)}")
            return False

    def is_loaded(self) -> bool:
        """Kiểm tra model đã được tải chưa"""
        return self.model is not None and self.dataset is not None

    def get_info(self) -> Dict[str, Any]:
        """Lấy thông tin về model"""
        if not self.is_loaded():
            return {}

        try:
            user_count = len(self.dataset.mapping()[0])
            item_count = len(self.dataset.mapping()[2])
            mine_count = len(self.mine_indices) if self.mine_indices is not None else 0

            return {
                "user_count": user_count,
                "item_count": item_count,
                "mine_count": mine_count,
                "metadata": self.model_data.get('metadata', {})
            }
        except Exception as e:
            logger.error(f"Lỗi khi lấy thông tin model: {str(e)}")
            return {}

    def get_users(self) -> List[Union[str, int]]:
        """Lấy danh sách người dùng"""
        if not self.is_loaded():
            return []

        try:
            user_map = self.dataset.mapping()[0]

            # Chuyển các key thành số nếu có thể
            users = []
            for k in user_map.keys():
                try:
                    users.append(int(float(k)))
                except:
                    users.append(str(k))

            return sorted(users)
        except Exception as e:
            logger.error(f"Lỗi khi lấy danh sách người dùng: {str(e)}")
            return []

    def get_courses(self, source: Optional[str] = None) -> List[Dict]:
        """
        Lấy danh sách khóa học

        Args:
            source: Nguồn dữ liệu (mine/udemy), nếu None thì lấy tất cả

        Returns:
            Danh sách thông tin khóa học
        """
        if not self.is_loaded() or self.courses_df is None:
            return []

        try:
            # Lọc theo nguồn nếu được chỉ định
            if source in ["mine", "udemy"]:
                if 'source' in self.courses_df.columns:
                    filtered_df = self.courses_df[self.courses_df['source'] == source]
                elif 'data_source' in self.courses_df.columns:
                    filtered_df = self.courses_df[self.courses_df['data_source'] == source]
                else:
                    # Fallback: Lọc theo mẫu ID nếu không có cột source
                    if source == "mine":
                        filtered_df = self.courses_df[self.courses_df['course_id'].astype(str).str.match(r'^CR\d+')]
                    else:
                        filtered_df = self.courses_df[~self.courses_df['course_id'].astype(str).str.match(r'^CR\d+')]
            else:
                filtered_df = self.courses_df

            # Chọn các cột cần thiết
            cols = ['course_id', 'title', 'category', 'price', 'level', 'language']
            cols = [c for c in cols if c in filtered_df.columns]

            # Xử lý trường hợp thiếu cột title
            if 'title' not in cols and 'course_title' in filtered_df.columns:
                filtered_df = filtered_df.copy()
                filtered_df['title'] = filtered_df['course_title']
                cols.append('title')

            # Tạo kết quả
            result_df = filtered_df[cols].copy()
            courses_list = result_df.to_dict(orient='records')

            return courses_list
        except Exception as e:
            logger.error(f"Lỗi khi lấy danh sách khóa học: {str(e)}")
            return []

    def recommend(self, user_id: Union[str, int], n: int = 10, mine_only: bool = True) -> Dict:
        """
        Đề xuất khóa học cho người dùng

        Args:
            user_id: ID người dùng
            n: Số lượng khóa học cần đề xuất
            mine_only: Chỉ đề xuất khóa học 'mine'

        Returns:
            Dict chứa các khóa học được đề xuất và thông tin liên quan
        """
        if not self.is_loaded():
            raise ValueError("Model chưa được tải")

        try:
            # 1. Lấy mapping từ dataset
            user_map, item_map = self.dataset.mapping()[0], self.dataset.mapping()[2]

            # Map ngược từ index sang ID
            idx_to_item = {v: k for k, v in item_map.items()}

            # Đảm bảo kiểu dữ liệu của user_id phù hợp với mapping
            sample_key = next(iter(user_map.keys()))
            if isinstance(sample_key, str):
                uid_key = str(user_id)
            else:
                uid_key = int(float(user_id))

            # Xử lý trường hợp đặc biệt với .0
            if isinstance(uid_key, int) or (isinstance(uid_key, str) and not uid_key.endswith('.0')):
                float_key = f"{uid_key}.0"
                if float_key in user_map:
                    uid_key = float_key

            # Kiểm tra user tồn tại
            if uid_key not in user_map:
                logger.warning(f"User {user_id} không có trong model")
                return {
                    "user_id": user_id,
                    "count": 0,
                    "mine_only": mine_only,
                    "error": f"User {user_id} không có trong model",
                    "recommendations": []
                }

            # Lấy index nội bộ của user
            uidx = user_map[uid_key]

            # 2. Xác định khóa học đã đánh giá (để loại bỏ)
            rated_courses = []
            if 'sampled_reviews' in self.model_data:
                reviews_df = self.model_data['sampled_reviews']
                # Lọc reviews của user
                user_reviews = reviews_df[
                    reviews_df["user_id"].astype(str) == str(uid_key)
                    ]
                if not user_reviews.empty:
                    rated_courses = user_reviews["course_id"].astype(str).tolist()

            # 3. Xác định danh sách khóa học để đề xuất
            if mine_only and self.mine_indices is not None:
                # Chỉ lấy khóa học 'mine' chưa được đánh giá
                candidate_indices = [idx for idx in self.mine_indices
                                     if idx_to_item[idx] not in rated_courses]

                # Nếu đã đánh giá tất cả khóa học 'mine', vẫn đề xuất tất cả
                if not candidate_indices:
                    candidate_indices = self.mine_indices
            else:
                # Lấy tất cả khóa học chưa được đánh giá
                all_items = list(item_map.keys())
                candidates = [i for i in all_items if i not in rated_courses] or all_items

                # Giới hạn số lượng candidate nếu quá nhiều
                if len(candidates) > 1000:
                    np.random.seed(42 + int(hash(str(user_id)) % 100000))
                    candidates = list(np.random.choice(candidates, 1000, replace=False))

                candidate_indices = [item_map[c] for c in candidates]

            # 4. Dự đoán điểm số
            scores = self.model.predict(uidx, candidate_indices, item_features=self.course_features)

            # 5. Chuẩn hóa điểm về thang 1-5
            if len(scores) > 0:
                min_score = scores.min()
                score_range = np.ptp(scores)
                norm_scores = 1 + 4 * (scores - min_score) / (score_range + 1e-9)
            else:
                norm_scores = []

            # 6. Sắp xếp và lấy top-n
            if len(scores) > 0:
                top_indices = np.argsort(-scores)[:min(n, len(scores))]
                selected_indices = [candidate_indices[i] for i in top_indices]
                top_raw = scores[top_indices]
                top_norm = norm_scores[top_indices]
            else:
                selected_indices = []
                top_raw = []
                top_norm = []

            # 7. Tạo kết quả trả về
            recs = []
            for idx, raw, norm_score in zip(selected_indices, top_raw, top_norm):
                # Lấy course_id từ index
                course_id = idx_to_item[idx]

                # Tạo thông tin cơ bản cho khóa học
                info = {
                    "course_id": course_id,
                    "score": float(norm_score),
                    "original_score": float(raw)
                }

                # Thêm thông tin chi tiết nếu có
                if self.courses_df is not None:
                    course_rows = self.courses_df[self.courses_df["course_id"].astype(str) == str(course_id)]
                    if not course_rows.empty:
                        row = course_rows.iloc[0]

                        # Thêm tên khóa học
                        title_col = None
                        for col in ['title', 'course_title']:
                            if col in row and pd.notna(row[col]):
                                title_col = col
                                break

                        if title_col:
                            info["title"] = row[title_col]
                        else:
                            info["title"] = f"Course {course_id}"

                        # Thêm các thông tin bổ sung
                        for field in ['category', 'price', 'level', 'language']:
                            if field in row and pd.notna(row[field]):
                                info[field] = row[field]

                recs.append(info)

            # 8. Tạo payload
            payload = {
                "user_id": user_id,
                "count": len(recs),
                "mine_only": mine_only,
                "recommendations": recs
            }

            return payload
        except Exception as e:
            logger.exception(f"Lỗi khi đề xuất khóa học: {str(e)}")
            raise