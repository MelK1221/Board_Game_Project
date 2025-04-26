
def func(x):
    return x + 1


# pytest will run all files of the form test_*.py or *_test.py in the current directory and its subdirectories.
def test_answer():
    assert func(4) == 5

