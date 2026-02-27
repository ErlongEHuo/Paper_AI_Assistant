import datetime
from time import sleep 
import time

def time_decorator(func):
    """
    装饰器：记录函数调用时间
    """
    def wrapper(*args, **kwargs):
        # 记录调用信息
        start_time =time.time()
        call_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"【日志】开始时间：{call_time} - 函数 {func.__name__} 被调用，参数：args={args}, kwargs={kwargs}")
        
        # 调用原函数
        result = func(*args, **kwargs)

        call_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 记录返回结果
        # print(f"【日志】函数 {func.__name__} 返回值：{result}")
        end_time =time.time()
        print(f'【日志】结束时间：{call_time} 执行时长：{(end_time-start_time)}秒',)
          
        return result
    return wrapper

@time_decorator
def test1():
    #睡眠5s
    print('开始')
    sleep(5)
    print('结束')


if __name__ == '__main__':
    test1()

