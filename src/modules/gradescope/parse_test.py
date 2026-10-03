import unittest

from src.modules.gradescope.main import Gradescope
from src.modules.interfaces import Module


COURSE_HTML = """
<html><body>
<table><tbody><tr role="row"><th>Ignore this other table</th></tr></tbody></table>
<table id="assignments-student-table">
  <tbody>
    <tr role="row">
      <th class="table--primaryLink"><a href="/courses/1/assignments/2">HW0</a></th>
      <td><div class="submissionStatus--text">No Submission</div></td>
      <td><time class="submissionTimeChart--dueDate" datetime="2026-10-08T06:59:00Z">Oct 07 at 11:59PM</time></td>
    </tr>
    <tr>
      <th class="table--primaryLink"><button>HW1</button></th>
      <td class="submissionStatus submissionStatus-complete">
        <div class="submissionStatus--text">Submitted</div>
      </td>
      <td><time class="submissionTimeChart--dueDate">Oct 09 at 11:59PM</time></td>
    </tr>
    <tr>
      <th class="table--primaryLink"><a href="/courses/1/assignments/9">No due date</a></th>
      <td><div class="submissionStatus--text">No Submission</div></td>
    </tr>
  </tbody>
</table>
</body></html>
"""


class ParseAssignmentsTest(unittest.TestCase):
    def test_reads_student_table_including_rows_without_role(self):
        page = Module.parse_html(COURSE_HTML)
        assignments = Gradescope._assignments_from_course_page(
            page, 'CSE 446', '/courses/1'
        )

        self.assertEqual([item['title'] for item in assignments], ['HW0', 'HW1'])
        self.assertFalse(assignments[0]['submitted'])
        self.assertTrue(assignments[1]['submitted'])
        self.assertEqual(
            assignments[0]['link'],
            'https://www.gradescope.com/courses/1/assignments/2'
        )
        self.assertIn('2026-10-08', assignments[0]['dueDate'])
        self.assertTrue(assignments[1]['dueDate'])


if __name__ == '__main__':
    unittest.main()
