from src.common import utils
from src.modules.interfaces import Module


class Gradescope(Module):
    ROOT = 'https://www.gradescope.com'

    def _init(self):
        # Extract authentication token from login page
        login_page_res = self.session.get(Gradescope.ROOT)
        login_page = Module.parse_html(login_page_res.text)
        token = None
        for form in login_page.find_all('form'):
            if form.get('action') == '/login':
                for input_element in form.find_all('input'):
                    if input_element.get('name') == 'authenticity_token':
                        token = input_element.get('value')

        if token is not None:
            # Login by imitating JSON payload found by:
            # Inspect -> Network -> Enter info and login -> View 'login' request payload
            login_payload = {
                'utf8': '✓',
                'authenticity_token': token,
                'session[email]': self.user,
                'session[password]': self.password,
                'session[remember_me]': 0,
                'commit': 'Log In',
                'session[remember_me_sso]': 0
            }
            login_response = self.session.post(
                Gradescope.ROOT + '/login',
                params=login_payload
            )
            history = login_response.history
            if len(history) > 0 and history[0].status_code == 302:
                self.initialized = True

    def _main(self, assignments: list):
        dashboard_res = self.session.get(Gradescope.ROOT + '/account')
        dashboard = Module.parse_html(dashboard_res.text)

        # Avoid "Instructor" section
        student_courses = dashboard.find_all('div', {'class': 'courseList'})[-1]
        current_courses = student_courses.find('div', {'class': 'courseList--coursesForTerm'})
        for course_entry in current_courses.find_all('a', {'class': 'courseBox'}):
            course_name = course_entry.find('h3', {'class': 'courseBox--shortname'}).text
            if course_name not in assignments:
                assignments[course_name] = []
            course_link = course_entry.get('href')

            # Retrieve assignment information
            course_dashboard_res = self.session.get(Gradescope.ROOT + course_link)
            course_dashboard = Module.parse_html(course_dashboard_res.text)
            for assignment in Gradescope._assignments_from_course_page(
                course_dashboard, course_name, course_link
            ):
                assignments[course_name].append(assignment)
            print(f"{course_name}: {len(assignments[course_name])} assignments")

    @staticmethod
    def _assignments_from_course_page(course_dashboard, course_name, course_link):
        """Reads the student assignment table from a course page."""

        assignment_table = course_dashboard.find('table', id='assignments-student-table')
        if assignment_table is None:
            assignment_table = course_dashboard.find('tbody')
        if assignment_table is None:
            print(f"No assignment table for '{course_name}'")
            return []

        tbody = assignment_table.find('tbody') or assignment_table
        parsed = []
        for row in tbody.find_all('tr'):
            date_string = Gradescope._get_assignment_due_date(row)
            title = Gradescope._get_assignment_title(row)
            if not date_string or not title:
                continue
            status = Gradescope._get_assignment_status(row)
            link = Gradescope._get_assignment_link(row, course_link)
            assignment = utils.get_assignment_dict(
                title,
                course_name,
                date_string,
                link,
                Gradescope._is_submitted(row, status)
            )
            if assignment is not None:
                parsed.append(assignment)
        return parsed

    @staticmethod
    def _get_assignment_title(row):
        """Returns the title of an assignment given its row in the table."""

        heading = row.find('th', class_='table--primaryLink')
        if heading is None:
            heading = row.find('th')
        if heading is None:
            return ''
        title = heading.find('a')
        if title is None:
            title = heading.find('button')
        if title is None:
            title = heading
        return title.get_text(strip=True)

    @staticmethod
    def _get_assignment_due_date(row):
        """Returns the due date of an assignment given its row in the table."""

        due_date = row.find('time', class_='submissionTimeChart--dueDate')
        if due_date is None:
            return None
        return due_date.get('datetime') or due_date.get_text(strip=True) or None

    @staticmethod
    def _get_assignment_status(row):
        """Returns the submission status text for an assignment row."""

        status = row.find('div', class_='submissionStatus--text')
        if status is None:
            status = row.find('div', class_='submissionStatus--score')
        if status is None:
            return ''
        return status.get_text(strip=True)

    @staticmethod
    def _is_submitted(row, status):
        status_cell = row.find('td', class_='submissionStatus')
        classes = status_cell.get('class', []) if status_cell is not None else []
        if 'submissionStatus-complete' in classes:
            return True
        return status not in ('', 'No Submission')

    @staticmethod
    def _get_assignment_link(row, course_link):
        """Returns a link to the assignment."""

        primary_link = row.find('th', class_='table--primaryLink')
        anchor = primary_link.find('a') if primary_link is not None else None
        link = course_link
        if anchor is not None and anchor.get('href'):
            link = anchor.get('href')
        if link.startswith('http'):
            return link
        return Gradescope.ROOT + link
