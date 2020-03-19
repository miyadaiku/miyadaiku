from pathlib import Path
from miyadaiku import loader


def test_walk_directory(sitedir):
    dir1 = (sitedir / 'dir1')
    dir1.mkdir()

    dir2 = dir1 / 'dir2'
    dir2.mkdir()

    file1 = (dir1 / 'file1')
    file1.write_text('')


    file2 = (dir2 / 'file2')
    file2.write_text('')

    (dir1 / 'test.bak').write_text('')

    results = loader.walk_directory(sitedir, set(["*.bak"]))
    all = sorted(results, key=lambda d:d['srcpath'])
    assert len(all) == 2

    assert all[0] == dict(srcpath=file2, contentpath=('dir1', 'dir2', 'file2'))
    assert all[1] == dict(srcpath=file1, contentpath=('dir1', 'file1'))


def test_walkpackage(sitedir):
    results = loader.walk_package('package1', 'contents', set(["*.bak"]))
    all = sorted(results, key=lambda d:d['srcpath'])
    
    assert len(all) == 7
    assert all[0] == {'package': 'package1', 'srcpath': 'contents/dir1/a', 'contentpath': ('dir1', 'a')}

