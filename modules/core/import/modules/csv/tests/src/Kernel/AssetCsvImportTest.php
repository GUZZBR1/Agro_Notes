<?php

declare(strict_types=1);

namespace Drupal\Tests\farm_import_csv\Kernel;

use Drupal\asset\Entity\Asset;
use Drupal\farm_id_tag\Plugin\Field\FieldType\IdTagItem;
use Drupal\taxonomy\Entity\Term;
use Drupal\text\Plugin\Field\FieldType\TextLongItem;
use PHPUnit\Framework\Attributes\Group;
use PHPUnit\Framework\Attributes\RunTestsInSeparateProcesses;

/**
 * Tests for asset CSV importers.
 */
#[Group('farm')]
#[RunTestsInSeparateProcesses]
class AssetCsvImportTest extends CsvImportTestBase {

  /**
   * {@inheritdoc}
   */
  protected static $modules = [
    'entity',
    'farm_entity',
    'farm_equipment',
    'farm_equipment_type',
    'farm_id_tag',
    'farm_land',
    'farm_land_types',
    'farm_location',
    'farm_map',
    'farm_parent',
    'geofield',
    'taxonomy',
  ];

  /**
   * {@inheritdoc}
   */
  public function setUp(): void {
    parent::setUp();
    $this->installConfig([
      'farm_id_tag',
      'farm_equipment',
      'farm_equipment_type',
      'farm_land',
      'farm_land_types',
    ]);

    // Add an asset to test parent relationship.
    $asset = Asset::create(['name' => 'Test parent', 'type' => 'equipment']);
    $asset->save();
  }

  /**
   * Test asset CSV importer.
   */
  public function testAssetCsvImport() {

    // Create a Tractor equipment type term.
    $term = Term::create([
      'name' => 'Tractor',
      'vid' => 'equipment_type',
    ]);
    $term->save();

    // Run the CSV import.
    $this->importCsv('equipment.csv', 'csv_asset:equipment');

    // Confirm that 3 assets have been created with the expected values
    // (in addition to the 1 we created in setUp() above).
    $assets = Asset::loadMultiple();
    $this->assertCount(4, $assets);
    $expected_values = [
      2 => [
        'name' => 'Old tractor',
        'manufacturer' => '',
        'model' => '',
        'serial_number' => '',
        'id_tag' => [
          'id' => '12345',
          'type' => '',
          'location' => '',
        ],
        'equipment_types' => [
          'Tractor',
        ],
        'parents' => [],
        'notes' => 'Inherited from Grandpa',
        'flags' => [
          'priority',
          'review',
        ],
        'archived' => TRUE,
      ],
      3 => [
        'name' => 'New tractor',
        'manufacturer' => '',
        'model' => '',
        'serial_number' => '',
        'id_tag' => [
          'id' => '67890',
          'type' => 'eid',
          'location' => 'trunk',
        ],
        'equipment_types' => [
          'Tractor',
        ],
        'parents' => [],
        'notes' => 'Purchased recently',
        'flags' => [
          'monitor',
        ],
        'archived' => FALSE,
      ],
      4 => [
        'name' => 'Baler',
        'manufacturer' => 'New Idea',
        'model' => '483 Round Baler',
        'serial_number' => '1234567890',
        'id_tag' => [
          'id' => '',
          'type' => '',
          'location' => '',
        ],
        'equipment_types' => [],
        'parents' => [
          'Test parent',
        ],
        'notes' => 'Makes big bales',
        'flags' => [],
        'archived' => FALSE,
      ],
    ];
    foreach ($assets as $id => $asset) {
      // Skip assets created in setup().
      if ($id <= 1) {
        continue;
      }

      // Confirm bundle and name are correct.
      $this->assertEquals('equipment', $asset->bundle());
      $this->assertEquals($expected_values[$id]['name'], $asset->label());

      // Confirm manufacturer, model, and serial_number are set.
      $this->assertEquals($expected_values[$id]['manufacturer'], $asset->get('manufacturer')->value);
      $this->assertEquals($expected_values[$id]['model'], $asset->get('model')->value);
      $this->assertEquals($expected_values[$id]['serial_number'], $asset->get('serial_number')->value);

      // Confirm ID tag is set.
      // If no tag ID is provided ensure we have an empty field.
      if (empty($expected_values[$id]['id_tag']['id'])) {
        $this->assertTrue($asset->get('id_tag')->isEmpty());
      }
      // Else check that all id_tag properties match.
      else {
        $id_tag = $asset->get('id_tag')->first();
        $this->assertInstanceOf(IdTagItem::class, $id_tag);
        $this->assertEquals($expected_values[$id]['id_tag']['id'], $id_tag->id);
        $this->assertEquals($expected_values[$id]['id_tag']['type'], $id_tag->type);
        $this->assertEquals($expected_values[$id]['id_tag']['location'], $id_tag->location);
      }

      // Confirm that equipment type is set.
      $equipment_types = $asset->get('equipment_type')->referencedEntities();
      $this->assertEquals(count($expected_values[$id]['equipment_types']), count($equipment_types));
      foreach ($equipment_types as $equipment_type) {
        $this->assertContains($equipment_type->label(), $expected_values[$id]['equipment_types']);
      }

      // Confirm that parent is set.
      $parents = $asset->get('parent')->referencedEntities();
      $this->assertEquals(count($expected_values[$id]['parents']), count($parents));
      foreach ($parents as $parent) {
        $this->assertContains($parent->label(), $expected_values[$id]['parents']);
      }

      // Confirm notes and status are set.
      $this->assertEquals($expected_values[$id]['notes'], $asset->get('notes')->value);
      $this->assertInstanceOf(TextLongItem::class, $asset->get('notes')->first());
      $this->assertEquals('default', $asset->get('notes')->first()->format);
      $this->assertEquals($expected_values[$id]['archived'], $asset->get('archived')->value);

      // Confirm that flags are set.
      if (!empty($expected_values[$id]['flags'])) {
        foreach ($asset->get('flag') as $flag) {
          $this->assertTRUE(in_array($flag->getValue()['value'], $expected_values[$id]['flags']));
        }
      }

      // Confirm revision message is set.
      $this->assertEquals('Imported via CSV.', $asset->getRevisionLogMessage());
    }

    // Run the land CSV import.
    $this->importCsv('land.csv', 'csv_asset:land');

    // Load the assets that were created and confirm they have expected values.
    $asset = Asset::load(5);
    $this->assertEquals('land', $asset->bundle());
    $this->assertEquals('Field A', $asset->label());
    $this->assertEquals('field', $asset->get('land_type')->value);
    $this->assertEquals('POINT(1 2)', $asset->get('intrinsic_geometry')->value);
    $this->assertEquals(1, $asset->get('is_location')->value);
    $this->assertEquals(1, $asset->get('is_fixed')->value);
    $this->assertEmpty($asset->get('archived')->value);
    $asset = Asset::load(6);
    $this->assertEquals('land', $asset->bundle());
    $this->assertEquals('Field B', $asset->label());
    $this->assertEquals('field', $asset->get('land_type')->value);
    $this->assertEquals('', $asset->get('intrinsic_geometry')->value);
    $this->assertEquals(0, $asset->get('is_location')->value);
    $this->assertEquals(0, $asset->get('is_fixed')->value);
    $this->assertEmpty($asset->get('archived')->value);
  }

}
