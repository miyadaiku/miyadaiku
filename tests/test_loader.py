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

    all = sorted(loader.walk_directory(sitedir, set(["*.bak"])))
    assert len(all) == 2
    assert all[0] == (str(file2), ('dir1', 'dir2', 'file2'))
    assert all[1] == (str(file1), ('dir1', 'file1'))


def test_walkpackage(sitedir):
    all = sorted(loader.walk_package('package1', 'contents', set(["*.bak"])))

    assert len(all) == 7
    assert all[0] == ('contents/dir1/a', ('dir1', 'a'))
    assert all[1] == ('contents/dir1/conf.yml', ('dir1', 'conf.yml'))
    assert all[2] == ('contents/dir1/dir2/b', ('dir1', 'dir2', 'b'))
    assert all[3] == ('contents/dir1/dir2/conf.yml', ('dir1', 'dir2', 'conf.yml'))
    assert all[4] == ('contents/dir1/dir3/c', ('dir1', 'dir3', 'c'))
    assert all[5] == ('contents/dir1/test.rst', ('dir1', 'test.rst'))
    assert all[6] == ('contents/dir4/dir5/d', ('dir4', 'dir5', 'd'))



