# Superseded run — không dùng làm kết luận nghiệm thu

Đây là lần chạy trước khi thêm regression force-exit và sửa Docker preflight. `docker-engine: PASS` trong results.json cũ là phân loại sai của bộ thu thập, do Docker CLI trả exit code 0 dù có lỗi kết nối.

Kết quả cuối nằm ở [../20261027-final/results.json](../20261027-final/results.json): Docker Engine BLOCKED. File `defect-mock-forceexit-before-fix.log` giữ bằng chứng lỗi mock trước khi sửa. Không xóa bằng chứng lần chạy trước.
