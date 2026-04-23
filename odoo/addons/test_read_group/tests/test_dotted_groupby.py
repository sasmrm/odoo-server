""" Test read_group grouping with dotted (one-hop M2O traversal) fields. """

from odoo.tests import common


@common.tagged('test_dotted_read_group')
class TestDottedGroupby(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner_a = cls.env['res.partner'].create({'name': 'Alpha'})
        cls.partner_b = cls.env['res.partner'].create({'name': 'Beta'})
        cls.Aggregate = cls.env['test_read_group.aggregate']
        cls.Aggregate.create([
            {'key': 1, 'value': 10, 'partner_id': cls.partner_a.id},
            {'key': 1, 'value': 20, 'partner_id': cls.partner_a.id},
            {'key': 2, 'value': 5,  'partner_id': cls.partner_b.id},
            {'key': 2, 'value': 7,  'partner_id': False},
        ])

    def test_group_by_parent_scalar(self):
        """ Group by M2O.name (scalar leaf on the comodel). """
        groups = self.Aggregate.read_group(
            domain=[('key', 'in', [1, 2])],
            fields=['value'],
            groupby=['partner_id.name'],
            lazy=False,
        )
        by_name = {g['partner_id.name']: g for g in groups}
        self.assertIn('Alpha', by_name)
        self.assertIn('Beta', by_name)
        self.assertEqual(by_name['Alpha']['value'], 30)
        self.assertEqual(by_name['Beta']['value'], 5)
        # the 'None' bucket (partner_id is NULL) appears as False
        self.assertIn(False, by_name)
        self.assertEqual(by_name[False]['value'], 7)

    def test_group_by_parent_m2o(self):
        """ Group by M2O.M2O (leaf is itself a many2one). """
        # partner.company_id is a stored M2O on res.partner
        company = self.env.company
        (self.partner_a | self.partner_b).write({'company_id': company.id})
        groups = self.Aggregate.read_group(
            domain=[('key', 'in', [1, 2])],
            fields=['value'],
            groupby=['partner_id.company_id'],
            lazy=False,
        )
        resolved = [g['partner_id.company_id'] for g in groups if g['partner_id.company_id']]
        self.assertTrue(resolved, "expected at least one non-null company group")
        for entry in resolved:
            self.assertIsInstance(entry, tuple)
            self.assertEqual(entry[0], company.id)

    def test_group_by_parent_scalar_domain(self):
        """ The __domain emitted for the group is usable to re-select the records. """
        groups = self.Aggregate.read_group(
            domain=[('key', 'in', [1, 2])],
            fields=['value'],
            groupby=['partner_id.name'],
            lazy=False,
        )
        alpha_group = next(g for g in groups if g['partner_id.name'] == 'Alpha')
        records = self.Aggregate.search(alpha_group['__domain'])
        self.assertEqual(sum(r.value for r in records), 30)
