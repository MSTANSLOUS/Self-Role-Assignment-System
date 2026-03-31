from flask import render_template
from flask import Blueprint
from flask import url_for
from flask import request
from flask import redirect
from .models import Role
from .models import db
from .models import User
import io
from flask import make_response
from xhtml2pdf import pisa

routes_pb = Blueprint("routes", __name__)



@routes_pb.route("/")
def index():
    # 1. Grab all roles from the database
    all_roles = Role.query.all()

    # 2. Pass 'all_roles' into your index.html file
    return render_template("index.html", roles=all_roles)




@routes_pb.route("/admin", methods=["GET", "POST"])
def admin():
    #checking the request
    if request.method == "POST":
        # 1. Grab the data from the admin form
        title = request.form.get('role_title')  # Make sure your HTML input name is 'role_title'
        spots = request.form.get('spots_available')  # Make sure your HTML input name is 'spots_available'
        desc = request.form.get('role_desc')  # Make sure your HTML input name is 'role_desc'

        # 2. Create a new Role object based on your model
        new_role = Role(role=title, description=desc, spots=int(spots))

        # 3. Save it to the database
        db.session.add(new_role)
        db.session.commit()

        print(f"Role '{title}' saved successfully!")
        return redirect(url_for('routes.admin'))

    # --- THIS IS THE NEW GET PART ---
    # 1. Grab all registered users from the database
    all_users = User.query.all()

    # NEW: 2. Grab all created roles from the database too!
    all_roles = Role.query.all()

    #if its GET just show the page
    return render_template("admin.html", users=all_users, roles=all_roles)




#register fro a role
@routes_pb.route("/register", methods=["POST"])
def register():
    user_name = request.form.get('full_name')
    user_email = request.form.get('student_email')
    selected_role = request.form.get('role_name')

    matched_role = Role.query.filter_by(role=selected_role).first()
    if matched_role:

        # NEW: 2. Check if there are actually spots left!
        if matched_role.spots > 0:
            new_user = User(name=user_name, email=user_email,
                            role_id=matched_role.id)  # This links the user to the specific role

            db.session.add(new_user)

            # NEW: 3. Subtract 1 spot from the matched role!
            matched_role.spots = matched_role.spots - 1

            db.session.commit()

    return redirect(url_for('routes.index'))


@routes_pb.route("/delete-user/<int:user_id>", methods=["POST"])
def delete_user(user_id):
    user_to_delete = User.query.get(user_id)

    if user_to_delete:
        """find the role the user was in"""
        matched_role = db.session.get(Role, user_to_delete.role_id)

        if matched_role:
            matched_role.spots = matched_role.spots + 1

        db.session.delete(user_to_delete)
        db.session.commit()

    return redirect(url_for('routes.admin'))


# Add this at the bottom of your Python routes file!
@routes_pb.route("/delete-role/<int:role_id>", methods=["POST"])
def delete_role(role_id):
    # 1. Grab the role from the DB
    role_to_delete = db.session.get(Role, role_id)

    if role_to_delete:
        # 2. Safety check: What if users are already registered for this role?
        # Let's find any users attached to this role and clear their role link
        linked_users = User.query.filter_by(role_id=role_id).all()
        for user in linked_users:
            # You can either delete the users or set their role_id to None.
            # Let's just delete them to keep your DB perfectly clean.
            db.session.delete(user)

        # 3. Delete the actual role
        db.session.delete(role_to_delete)
        db.session.commit()
        print(f"Role and its registered users successfully removed.")
    else:
        print("Role not found.")

    return redirect(url_for('routes.admin'))





@routes_pb.route("/export-pdf")
def export_pdf():
    # 1. Grab all registered users from the database
    users = User.query.all()

    # 2. Create the HTML layout for the PDF (Tailwind won't work perfectly in PDF, so we use standard CSS)
    html_content = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Helvetica, Arial, sans-serif; color: #334155; margin: 30px; }}
            .header {{ text-align: center; margin-bottom: 30px; border-bottom: 2px solid #ef4444; padding-bottom: 10px; }}
            .title {{ font-size: 24px; font-weight: bold; color: #1e293b; }}
            .tag {{ font-size: 10px; color: #94a3b8; text-transform: uppercase; letter-spacing: 1px; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
            th {{ background-color: #f8fafc; color: #64748b; font-size: 11px; text-transform: uppercase; text-align: left; padding: 12px; border-bottom: 2px solid #e2e8f0; }}
            td {{ padding: 12px; font-size: 13px; border-bottom: 1px solid #f1f5f9; }}
            .role-badge {{ background-color: #eff6ff; color: #2563eb; padding: 3px 8px; border-radius: 12px; font-size: 11px; font-weight: bold; }}
            .footer {{ text-align: center; margin-top: 40px; font-size: 12px; color: #64748b; }}
            .signature {{ font-weight: bold; color: #0f172a; font-size: 14px; margin-top: 5px; }}
        </style>
    </head>
    <body>
        <div class="header">
            <div class="title">Current Registrations Report</div>
            <div class="tag">System Control Panel</div>
        </div>

        <table>
            <thead>
                <tr>
                    <th>Full Name</th>
                    <th>Student Email</th>
                    <th>Selected Role</th>
                </tr>
            </thead>
            <tbody>
    """

    for user in users:
        html_content += f"""
                <tr>
                    <td><b>{user.name}</b></td>
                    <td>{user.email}</td>
                    <td><span class="role-badge">{user.role.role}</span></td>
                </tr>
        """

    html_content += f"""
            </tbody>
        </table>

        <div class="footer">
            <p>Report generated successfully.</p>
            <div class="signature">Generated by: MsSTANSLOUS </div>
        </div>
    </body>
    </html>
    """

    # 3. Convert HTML to PDF in memory
    pdf_buffer = io.BytesIO()
    pisa_status = pisa.CreatePDF(html_content, dest=pdf_buffer)

    if pisa_status.err:
        return "Error generating PDF", 500

    pdf_buffer.seek(0)

    # 4. Return the file to the browser as a download
    response = make_response(pdf_buffer.read())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'attachment; filename=registrations_report.pdf'

    return response