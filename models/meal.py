from database import db

class Meal(db.Model):
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    description = db.Column(db.String(200), nullable=False)
    datetime = db.Column(db.String(80), nullable=False)
    within_diet = db.Column(db.Boolean, nullable=False)

    def __repr__(self):
        return f'<Meal {self.id} - {self.name}>'