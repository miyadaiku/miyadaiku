from miyadaiku import strip_directory_index

def test_strip_directory_index():
    # real cases
    assert strip_directory_index('index.html', 'index.html') == ''
    assert strip_directory_index('hoge.html', 'hoge.html') == ''
    assert strip_directory_index('hoge.html', 'fuga.html') == 'hoge.html'
    assert strip_directory_index('foo/bar.html', 'bar.html') == 'foo/'
    assert strip_directory_index('foo/bar.html', 'foo.html') == 'foo/bar.html'

    # abs path simulation
    assert strip_directory_index('/', 'hoge.html') == '/'
    assert strip_directory_index('/index.html', 'index.html') == '/'
    assert strip_directory_index('/hoge.html', 'fuga.html') == '/hoge.html'
    assert strip_directory_index('/foo/bar.html', 'bar.html') == '/foo/'
    assert strip_directory_index('/foo/bar.html', 'foo.html') == '/foo/bar.html'

    # URL simulation
    assert strip_directory_index('https://example.com', 'hoge.html') == 'https://example.com'
    assert strip_directory_index('https://example.com/', 'hoge.html') == 'https://example.com/'
    assert strip_directory_index('https://example.com/index.html', 'index.html') == 'https://example.com/'
    assert strip_directory_index('https://example.com/hoge.html', 'hoge.html') == 'https://example.com/'
    assert strip_directory_index('https://example.com/hoge.html', 'fuga.html') == 'https://example.com/hoge.html'
    assert strip_directory_index('https://example.com/foo/bar.html', 'bar.html') == 'https://example.com/foo/'
    assert strip_directory_index('https://example.com/foo/bar.html', 'foo.html') == 'https://example.com/foo/bar.html'
