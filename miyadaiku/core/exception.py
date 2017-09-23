import io
import traceback
import jinja2.exceptions
from . import utils


class MiyadaikuBuildError(Exception):
    filename = None
    lineno = None
    source = None
    tb = None

    def __init__(self, e, content, srcfilename, src):
        args = e.args
        if not srcfilename:
            srcifilename = content.srcfilename
        if isinstance(e, jinja2.exceptions.TemplateSyntaxError):
            lines = utils.nthlines(src, e.lineno)
            msg = f'''{srcfilename}:{e.lineno} {str(e)}
{lines}
'''
            args = (msg,)

        else:
            lineno = self._get_lineno(e, srcfilename)
            if lineno is not None:
                args = (args[0] + self._get_src(content, lineno, srcfilename, src,), )

        super().__init__(*args)

        self.pagefilename = content.srcfilename
        self.srcilfename = srcfilename
        self.exctype = e.__class__.__name__

    def _get_src(self, content, lineno, srcfilename, src):
        if not src:
            try:
                env = content.site.jinjaenv
                src = env.loader.get_source(env, srcfilename)[0]
            except jinja2.exceptions.TemplateNotFound:
                src = ''

        lines = utils.nthlines(src, lineno)
        s = f'''
Last template: {srcfilename}: {lineno}
{lines}
'''
        return s

    def _get_lineno(self, e, srcfilename):
        tbs = list(traceback.walk_tb(e.__traceback__))
        tbs.reverse()
        for tb in tbs:
            if tb[0].f_code.co_filename == srcfilename:
                return tb[0].f_lineno

    def to_dict(self):
        return dict(exctype=self.exctype, args=self.args, pagefilename=self.pagefilename,
                    srcfilename=self.srcilfename)
