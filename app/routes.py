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
    # Handle POST request (create new role)
    if request.method == "POST":
        title = request.form.get('role_title')
        spots = request.form.get('spots_available')
        desc = request.form.get('role_desc')
        
        new_role = Role(role=title, description=desc, spots=int(spots))
        db.session.add(new_role)
        db.session.commit()
        
        print(f"Role '{title}' saved successfully!")
        return redirect(url_for('routes.admin'))
    
    # Handle GET request - with pagination
    # Get page number from URL, default to 1
    page = request.args.get('page', 1, type=int)
    per_page = 10  # Show 10 users per page
    
    # Get paginated users
    pagination = User.query.paginate(page=page, per_page=per_page, error_out=False)
    users = pagination.items
    total_users = pagination.total
    total_pages = pagination.pages
    
    # Get all roles (no pagination needed for roles)
    all_roles = Role.query.all()
    
    return render_template(
        "admin.html", 
        users=users, 
        roles=all_roles,
        pagination=pagination,
        current_page=page,
        total_pages=total_pages,
        total_users=total_users,
        per_page=per_page
    )



@routes_pb.route("/admin/data")
def admin_data():
    """AJAX endpoint for smooth pagination"""
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    pagination = User.query.paginate(page=page, per_page=per_page, error_out=False)
    users = pagination.items
    
    # Render just the table HTML (no full page)
    html = render_template("admin_table.html", users=users)
    
    return {
        "html": html,
        "current_page": page,
        "total_pages": pagination.pages,
        "total_users": pagination.total,
        "per_page": per_page
    }




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
    
    # Get current date for the report
    from datetime import datetime
    current_date = datetime.now().strftime("%B %d, %Y at %I:%M %p")
    
    # Count total registrations and unique roles
    total_users = len(users)
    unique_roles = len(set(user.role.role for user in users)) if users else 0

    # 2. Create the HTML layout for the PDF with xhtml2pdf-compatible CSS
    html_content = f"""
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Registrations Report</title>
        <style>
            body {{
                font-family: Helvetica, Arial, sans-serif;
                color: #333333;
                margin: 20px;
                line-height: 1.4;
            }}
            
            /* Header */
            .header {{
                text-align: center;
                margin-bottom: 30px;
                padding-bottom: 15px;
                border-bottom: 2px solid #2563eb;
            }}
            
            .title {{
                font-size: 24px;
                font-weight: bold;
                color: #111111;
                margin-bottom: 5px;
            }}
            
            .subtitle {{
                font-size: 12px;
                color: #666666;
                margin-top: 5px;
            }}
            
            .date {{
                font-size: 10px;
                color: #888888;
                margin-top: 8px;
            }}
            
            /* Stats Cards - Using tables for compatibility */
            .stats-container {{
                width: 100%;
                margin-bottom: 30px;
            }}
            
            .stat-card {{
                background-color: #f5f5f5;
                border: 1px solid #dddddd;
                padding: 12px;
                text-align: center;
                width: 30%;
            }}
            
            .stat-number {{
                font-size: 28px;
                font-weight: bold;
                color: #2563eb;
            }}
            
            .stat-label {{
                font-size: 9px;
                color: #666666;
                text-transform: uppercase;
                margin-top: 5px;
            }}
            
            /* Table Styles */
            .registrations-table {{
                width: 100%;
                border-collapse: collapse;
                margin: 20px 0;
                font-size: 11px;
            }}
            
            .registrations-table th {{
                background-color: #1e293b;
                color: white;
                font-weight: bold;
                padding: 10px 8px;
                text-align: left;
                border: 1px solid #334155;
            }}
            
            .registrations-table td {{
                padding: 8px;
                border: 1px solid #dddddd;
                color: #333333;
            }}
            
            .registrations-table tr:nth-child(even) {{
                background-color: #f9f9f9;
            }}
            
            .role-badge {{
                background-color: #dbeafe;
                color: #1e40af;
                padding: 3px 8px;
                font-weight: bold;
                font-size: 9px;
            }}
            
            /* Footer with Signatures */
            .footer {{
                margin-top: 40px;
                padding-top: 20px;
            }}
            
            .signatures-container {{
                width: 100%;
                margin-top: 20px;
            }}
            
            .signature-box {{
                width: 45%;
                text-align: center;
            }}
            
            .signature-line {{
                width: 80%;
                margin: 0 auto 5px auto;
                border-top: 1px solid #999999;
            }}
            
            .signature-name {{
                font-size: 11px;
                font-weight: bold;
                color: #111111;
                margin-bottom: 3px;
            }}
            
            .signature-title {{
                font-size: 8px;
                color: #666666;
                text-transform: uppercase;
            }}
            
            .signature-date {{
                font-size: 7px;
                color: #888888;
                margin-top: 4px;
            }}
            
            .stamp {{
                font-size: 8px;
                color: #2563eb;
                font-weight: bold;
                margin-top: 6px;
            }}
            
            .footer-note {{
                text-align: center;
                margin-top: 25px;
                padding-top: 12px;
                border-top: 1px solid #dddddd;
                font-size: 7px;
                color: #888888;
            }}
            
            .empty-state {{
                text-align: center;
                padding: 40px;
                color: #888888;
            }}
        </style>
    </head>
    <body>
        <!-- Header -->
        <div class="header">
            <div class="title">Registrations Report</div>
            <div class="subtitle">Role Assignment System</div>
            <div class="date">Generated on {current_date}</div>
        </div>
    """
    
    # Add statistics cards if there are users (using table for layout)
    if users:
        html_content += f"""
        <table class="stats-container" cellpadding="0" cellspacing="0" style="width: 100%; margin-bottom: 30px;">
            <tr>
                <td class="stat-card" style="background-color: #f5f5f5; border: 1px solid #dddddd; padding: 12px; text-align: center;">
                    <div class="stat-number">{total_users}</div>
                    <div class="stat-label">Total Registrations</div>
                </td>
                <td style="width: 5%;"></td>
                <td class="stat-card" style="background-color: #f5f5f5; border: 1px solid #dddddd; padding: 12px; text-align: center;">
                    <div class="stat-number">{unique_roles}</div>
                    <div class="stat-label">Roles Filled</div>
                </td>
                <td style="width: 5%;"></td>
                <td class="stat-card" style="background-color: #f5f5f5; border: 1px solid #dddddd; padding: 12px; text-align: center;">
                    <div class="stat-number">{datetime.now().strftime("%b %d")}</div>
                    <div class="stat-label">Report Date</div>
                </td>
            </tr>
        </table>
        """
    
    # Table Section
    if users:
        html_content += """
        <table class="registrations-table" cellpadding="0" cellspacing="0">
            <thead>
                <tr>
                    <th style="width: 30%;">Full Name</th>
                    <th style="width: 45%;">Email Address</th>
                    <th style="width: 25%;">Selected Role</th>
                </tr>
            </thead>
            <tbody>
        """
        
        for user in users:
            html_content += f"""
                <tr>
                    <td style="font-weight: 500; padding: 8px; border: 1px solid #dddddd;">{user.name}</td>
                    <td style="padding: 8px; border: 1px solid #dddddd;">{user.email}</td>
                    <td style="padding: 8px; border: 1px solid #dddddd;"><span class="role-badge">{user.role.role}</span></td>
                </tr>
            """
        
        html_content += """
            </tbody>
        </table>
        """
    else:
        html_content += """
        <div class="empty-state">
            <p>No registrations found in the system.</p>
            <p style="font-size: 10px; margin-top: 8px;">Register some roles to see them here</p>
        </div>
        """
    
    # Footer with TWO Signatures - Using table for layout
    html_content += f"""
        <div class="footer">
            <table class="signatures-container" cellpadding="0" cellspacing="0" style="width: 100%; margin-top: 30px;">
                <tr>
                    <!-- Left Signature - MsSTANSLOUS -->
                    <td class="signature-box" style="width: 50%; text-align: center;">
                        <div class="signature-line" style="width: 70%; margin: 0 auto 8px auto; border-top: 1px solid #999999;"></div>
                        <div class="signature-name">MsSTANSLOUS</div>
                        <div class="signature-title">System Developer</div>
                        <div class="signature-date">Generated: {current_date}</div>
                        <div class="stamp">✦ DIGITAL SIGNATURE ✦</div>
                    </td>
                    
                    <!-- Right Signature - System Admin Rejoice -->
                    <td class="signature-box" style="width: 50%; text-align: center;">
                        <div class="signature-line" style="width: 70%; margin: 0 auto 8px auto; border-top: 1px solid #999999;"></div>
                        <div class="signature-name">Rejoice</div>
                        <div class="signature-title">System Administrator</div>
                        <div class="signature-date">Authorized: {datetime.now().strftime("%B %d, %Y")}</div>
                        <div class="stamp">✓ APPROVED ✓</div>
                    </td>
                </tr>
            </table>
            
            <!-- Report Footer Note -->
            <div class="footer-note">
                This is a computer-generated document. No physical signature is required.<br/>
                Role Assignment System • MsSTANSLOUS • All Rights Reserved
            </div>
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