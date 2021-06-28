from miyadaiku import strip_directory_index

def test_strip_directory_index():
    assert strip_directory_index('index.html', 'index.html') == ''
    assert strip_directory_index('hoge.html', 'hoge.html') == ''
    assert strip_directory_index('hoge.html', 'fuga.html') == 'hoge.html'
    assert strip_directory_index('foo/bar.html', 'bar.html') == 'foo/'
    assert strip_directory_index('foo/bar.html', 'foo.html') == 'foo/bar.html'
