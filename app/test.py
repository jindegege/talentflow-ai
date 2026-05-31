# 导入所需的库
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
import numpy as np

# --- 数据准备 
data = {
    '预估薪资': [43000, 150000, 57000, 80000, 120000, 45000, 130000, 60000, 180000, 50000,
               95000, 110000, 70000, 160000, 40000, 140000, 90000, 105000, 75000, 170000],
    '是否会购买': [0, 1, 0, 0, 1, 0, 1, 0, 1, 0,
                 1, 1, 0, 1, 0, 1, 1, 1, 0, 1]
}
df = pd.DataFrame(data)

# 确保输出结果与代码步骤对应
print("--- 算法测试代码 ---")

# ① 划分特征X与标签y（字段名：是否会购买）
# 特征X是'预估薪资'，标签y是'是否会购买'
X = df[['预估薪资']]
y = df['是否会购买']
print("\n① 特征X与标签y划分完成。")


# ② 按照8:2的比例，随机划分为训练集和测试集
# test_size=0.2 表示测试集占20%，random_state用于保证每次划分结果一致
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
print("\n② 数据集已按8:2比例随机划分为训练集和测试集。")
# print(f"训练集大小: {len(X_train)}, 测试集大小: {len(X_test)}")


# ③ 将训练数据特征、测试数据特征分别转换成二维数组
# 虽然X_train和X_test已经是二维的DataFrame，但此步骤明确要求转换。
# .values 或 .to_numpy() 将其转换为numpy数组，.reshape(-1, 1) 确保其为 (n_samples, n_features) 的二维形状
X_train_2d = X_train.values.reshape(-1, 1)
X_test_2d = X_test.values.reshape(-1, 1)
print("\n③ 训练集和测试集的特征已转换为二维数组。")
# print(f"X_train_2d 形状: {X_train_2d.shape}")
# print(f"X_test_2d 形状: {X_test_2d.shape}")


# ④ 定义逻辑回归模型，用划分后的数据在训练集上训练模型
# 初始化逻辑回归模型
model = LogisticRegression()
# 使用训练集数据训练模型
model.fit(X_train_2d, y_train)
print("\n④ 逻辑回归模型已定义并在训练集上完成训练。")


# ⑤ 输出测试集的准确度
# 使用模型在测试集上进行评估，得到准确度分数
accuracy = model.score(X_test_2d, y_test)
print(f"\n⑤ 测试集的准确度: {accuracy:.4f}")


# ⑥ 输出测试集的预测值
# 使用训练好的模型对测试集特征进行预测
y_pred = model.predict(X_test_2d)
print("\n⑥ 测试集的预测值:")
print(y_pred)