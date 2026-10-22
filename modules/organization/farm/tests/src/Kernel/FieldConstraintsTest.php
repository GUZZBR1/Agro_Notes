<?php

declare(strict_types=1);

namespace Drupal\Tests\farm_farm\Kernel;

use Drupal\KernelTests\KernelTestBase;
use Drupal\Tests\user\Traits\UserCreationTrait;
use Drupal\asset\Entity\AssetInterface;
use Drupal\farm_farm\Plugin\Validation\Constraint\AssetGroupAssignmentFarm;
use Drupal\farm_farm\Plugin\Validation\Constraint\AssetMovementFarm;
use Drupal\farm_farm\Plugin\Validation\Constraint\AssetParentFarm;
use Drupal\farm_farm\Plugin\Validation\Constraint\LogAssetFarm;
use PHPUnit\Framework\Attributes\Group;
use PHPUnit\Framework\Attributes\RunTestsInSeparateProcesses;

/**
 * Field constraint tests for Farm organization module.
 */
#[Group('farm')]
#[RunTestsInSeparateProcesses]
class FieldConstraintsTest extends KernelTestBase {

  use UserCreationTrait;

  /**
   * {@inheritdoc}
   */
  protected static $modules = [
    'asset',
    'entity',
    'entity_reference_revisions',
    'entity_reference_validators',
    'farm_entity',
    'farm_entity_access',
    'farm_equipment',
    'farm_equipment_type',
    'farm_farm',
    'farm_farm_test',
    'farm_field',
    'farm_group',
    'farm_inventory',
    'farm_location',
    'farm_log',
    'farm_log_asset',
    'farm_log_quantity',
    'farm_map',
    'farm_parent',
    'farm_quantity_standard',
    'fraction',
    'geofield',
    'log',
    'options',
    'organization',
    'quantity',
    'state_machine',
    'system',
    'taxonomy',
    'text',
    'user',
    'views',
  ];

  /**
   * {@inheritdoc}
   */
  protected function setUp(): void {
    parent::setUp();
    $this->installEntitySchema('asset');
    $this->installEntitySchema('log');
    $this->installEntitySchema('organization');
    $this->installEntitySchema('quantity');
    $this->installEntitySchema('user');
    $this->installConfig([
      'farm_equipment',
      'farm_equipment_type',
      'farm_farm',
      'farm_farm_test',
      'farm_group',
      'farm_location',
      'farm_log_asset',
      'farm_quantity_standard',
    ]);

    // Create and login a user with access to view any organization. This is
    // necessary to validate the asset entities below, because the entity
    // module's query access handler enforces view access to referenced entities
    // during validation.
    $user = $this->createUser(['view any organization']);
    $this->container->get('current_user')->setAccount($user);
  }

  /**
   * Test AssetParentFarm constraint.
   */
  public function testAssetParentFarmConstraint() {
    $entity_type_manager = $this->container->get('entity_type.manager');
    $asset_storage = $entity_type_manager->getStorage('asset');
    $organization_storage = $entity_type_manager->getStorage('organization');

    // Create two farm organizations.
    $farm1 = $organization_storage->create([
      'type' => 'farm',
      'name' => $this->randomMachineName(),
    ]);
    $farm1->save();
    $farm2 = $organization_storage->create([
      'type' => 'farm',
      'name' => $this->randomMachineName(),
    ]);
    $farm2->save();

    // Create two assets, one in each farm.
    $asset1 = $asset_storage->create([
      'type' => 'test',
      'name' => $this->randomMachineName(),
      'farm' => [$farm1],
    ]);
    $asset1->save();
    $asset2 = $asset_storage->create([
      'type' => 'test',
      'name' => $this->randomMachineName(),
      'farm' => [$farm2],
    ]);
    $asset2->save();

    // Attempt to make the first asset a parent of the second.
    $asset2->set('parent', [$asset1]);
    $violations = $asset2->validate();

    // Confirm that a AssetParentFarm constraint violation was added because the
    // asset has a parent in a different farm.
    $this->assertEquals(1, $violations->count());
    $this->assertInstanceOf(AssetParentFarm::class, $violations->get(0)->getConstraint());

    // Move the second asset to the same farm as the first.
    $asset2->set('farm', [$farm1]);
    $asset2->save();

    // Confirm that it now validates.
    $violations = $asset1->validate();
    $this->assertEquals(0, $violations->count());

    // Save the parent hierarchy.
    $asset2->save();

    // Attempt to move the first asset to the second farm.
    $asset1->set('farm', [$farm2]);
    $violations = $asset1->validate();

    // Confirm that a AssetParentFarm constraint violation was added because the
    // asset has a child in a different farm.
    $this->assertEquals(1, $violations->count());
    $this->assertInstanceOf(AssetParentFarm::class, $violations->get(0)->getConstraint());

    // Reset the first asset to the first farm and confirm that it validates.
    $asset1->set('farm', [$farm1]);
    $violations = $asset1->validate();
    $this->assertEquals(0, $violations->count());

    // Remove farm assignment from both assets, save them, and confirm that they
    // both validate.
    $asset1->set('farm', []);
    $asset1->save();
    $asset2->set('farm', []);
    $asset2->save();
    $violations = $asset1->validate();
    $this->assertEquals(0, $violations->count());
    $violations = $asset2->validate();
    $this->assertEquals(0, $violations->count());
  }

  /**
   * Test log asset reference constraints.
   */
  public function testLogAssetConstraints() {
    $entity_type_manager = $this->container->get('entity_type.manager');
    $asset_storage = $entity_type_manager->getStorage('asset');
    $log_storage = $this->container->get('entity_type.manager')->getStorage('log');
    $organization_storage = $entity_type_manager->getStorage('organization');
    $quantity_storage = $entity_type_manager->getStorage('quantity');

    // Create two assets.
    // Both are equipment and are locations so that they can be referenced in
    // the asset, equipment, and location fields of a log.
    $asset1 = $asset_storage->create([
      'type' => 'equipment',
      'name' => $this->randomMachineName(),
      'is_location' => TRUE,
    ]);
    $asset1->save();
    $asset2 = $asset_storage->create([
      'type' => 'equipment',
      'name' => $this->randomMachineName(),
      'is_location' => TRUE,
    ]);
    $asset2->save();

    // Confirm that a log validates when it references both assets.
    $this->assertLogAssetReferenceValidates($asset1, $asset2);

    // Create two farm organizations.
    $farm1 = $organization_storage->create([
      'type' => 'farm',
      'name' => $this->randomMachineName(),
    ]);
    $farm1->save();
    $farm2 = $organization_storage->create([
      'type' => 'farm',
      'name' => $this->randomMachineName(),
    ]);
    $farm2->save();

    // Assign the first asset to the first farm.
    $asset1->set('farm', [$farm1]);
    $asset1->save();

    // Confirm that a log does not validate when it references both assets.
    $this->assertLogAssetReferenceValidates($asset1, $asset2, FALSE);

    // Add the second asset to the first farm and confirm that a log validates
    // when it references both.
    $asset2->set('farm', [$farm1]);
    $asset2->save();
    $this->assertLogAssetReferenceValidates($asset1, $asset2);

    // Add the second asset to the second farm and confirm that a log does not
    // validate when it references both.
    $asset2->set('farm', [$farm2]);
    $asset2->save();
    $this->assertLogAssetReferenceValidates($asset1, $asset2, FALSE);

    // Create a quantity with an asset inventory adjustment, referenced by a
    // log that references the other asset, and confirm that the log does not
    // validate.
    $quantity = $quantity_storage->create([
      'type' => 'standard',
      'value' => 1,
      'inventory_adjustment' => 'reset',
      'inventory_asset' => [$asset1],
    ]);
    $quantity->save();
    $log = $log_storage->create([
      'type' => 'test',
      'asset' => [$asset2],
      'quantity' => [$quantity],
    ]);
    $violations = $log->validate();
    $this->assertEquals(1, $violations->count());
    $this->assertInstanceOf(LogAssetFarm::class, $violations->get(0)->getConstraint());

    // Move the second asset to the first farm and confirm that the log
    // validates.
    $asset2->set('farm', [$farm1]);
    $asset2->save();
    $violations = $log->validate();
    $this->assertEquals(0, $violations->count());
  }

  /**
   * Helper method for testing log asset references.
   *
   * @param \Drupal\asset\Entity\AssetInterface $asset1
   *   The first asset.
   * @param \Drupal\asset\Entity\AssetInterface $asset2
   *   The second asset.
   * @param bool $validates
   *   Whether validation is expected (defaults to TRUE).
   */
  protected function assertLogAssetReferenceValidates(AssetInterface $asset1, AssetInterface $asset2, bool $validates = TRUE) {
    $log_storage = $this->container->get('entity_type.manager')->getStorage('log');

    // Test assets in the asset reference field.
    $log = $log_storage->create([
      'type' => 'test',
      'asset' => [$asset1, $asset2],
    ]);
    $violations = $log->validate();
    $this->assertEquals($validates ? 0 : 1, $violations->count());
    if (!$validates) {
      $this->assertInstanceOf(LogAssetFarm::class, $violations->get(0)->getConstraint());
    }

    // Test assets in the equipment reference field.
    $log = $log_storage->create([
      'type' => 'test',
      'equipment' => [$asset1, $asset2],
    ]);
    $violations = $log->validate();
    $this->assertEquals($validates ? 0 : 1, $violations->count());
    if (!$validates) {
      $this->assertInstanceOf(LogAssetFarm::class, $violations->get(0)->getConstraint());
    }

    // Test assets in the location reference field.
    $log = $log_storage->create([
      'type' => 'test',
      'location' => [$asset1, $asset2],
    ]);
    $violations = $log->validate();
    $this->assertEquals($validates ? 0 : 1, $violations->count());
    if (!$validates) {
      $this->assertInstanceOf(LogAssetFarm::class, $violations->get(0)->getConstraint());
    }

    // Test assets in asset and location fields.
    $log = $log_storage->create([
      'type' => 'test',
      'asset' => [$asset1],
      'location' => [$asset2],
    ]);
    $violations = $log->validate();
    $this->assertEquals($validates ? 0 : 1, $violations->count());
    if (!$validates) {
      $this->assertInstanceOf(LogAssetFarm::class, $violations->get(0)->getConstraint());
    }

    // Test assets in asset and equipment fields.
    $log = $log_storage->create([
      'type' => 'test',
      'asset' => [$asset1],
      'equipment' => [$asset2],
    ]);
    $violations = $log->validate();
    $this->assertEquals($validates ? 0 : 1, $violations->count());
    if (!$validates) {
      $this->assertInstanceOf(LogAssetFarm::class, $violations->get(0)->getConstraint());
    }

    // Test assets in equipment and location fields.
    $log = $log_storage->create([
      'type' => 'test',
      'equipment' => [$asset1],
      'location' => [$asset2],
    ]);
    $violations = $log->validate();
    $this->assertEquals($validates ? 0 : 1, $violations->count());
    if (!$validates) {
      $this->assertInstanceOf(LogAssetFarm::class, $violations->get(0)->getConstraint());
    }
  }

  /**
   * Test movement constraints.
   */
  public function testMovementConstraints() {
    $entity_type_manager = $this->container->get('entity_type.manager');
    $asset_storage = $entity_type_manager->getStorage('asset');
    $log_storage = $entity_type_manager->getStorage('log');
    $organization_storage = $entity_type_manager->getStorage('organization');

    // Create two farm organizations.
    $farm1 = $organization_storage->create([
      'type' => 'farm',
      'name' => $this->randomMachineName(),
    ]);
    $farm1->save();
    $farm2 = $organization_storage->create([
      'type' => 'farm',
      'name' => $this->randomMachineName(),
    ]);
    $farm2->save();

    // Create two location assets, one in each farm.
    $location1 = $asset_storage->create([
      'type' => 'test',
      'name' => $this->randomMachineName(),
      'is_location' => TRUE,
      'farm' => [$farm1],
    ]);
    $location1->save();
    $location2 = $asset_storage->create([
      'type' => 'test',
      'name' => $this->randomMachineName(),
      'is_location' => TRUE,
      'farm' => [$farm2],
    ]);
    $location2->save();

    // Create a movable asset in the first farm.
    $asset = $asset_storage->create([
      'type' => 'test',
      'name' => $this->randomMachineName(),
      'is_fixed' => FALSE,
      'farm' => [$farm1],
    ]);

    // Confirm that the asset validates.
    $violations = $asset->validate();
    $this->assertEquals(0, $violations->count());

    // Save the asset.
    $asset->save();

    // Create a log that moves the asset to location 2.
    $log = $log_storage->create([
      'type' => 'test',
      'asset' => [$asset],
      'location' => [$location2],
      'is_movement' => TRUE,
    ]);

    // Confirm that a LogAssetFarm constraint violation was added because the
    // asset is not in the same farm as location 2.
    $violations = $log->validate();
    $this->assertEquals(1, $violations->count());
    $this->assertInstanceOf(LogAssetFarm::class, $violations->get(0)->getConstraint());

    // Change the log location to location 1.
    $log->set('location', [$location1]);

    // Confirm that the log validates.
    $violations = $log->validate();
    $this->assertEquals(0, $violations->count());

    // Save the log.
    $log->save();

    // Attempt to change the asset to the second farm and confirm that an
    // AssetMovementFarm constraint violation was added because the asset has
    // a movement log associated with it.
    $asset->set('farm', [$farm2]);
    $violations = $asset->validate();
    $this->assertEquals(1, $violations->count());
    $this->assertInstanceOf(AssetMovementFarm::class, $violations->get(0)->getConstraint());

    // Attempt to change location 1 to the second farm and confirm that an
    // AssetMovementFarm constraint violation was added because the location
    // asset has a movement log associated with it.
    $location1->set('farm', [$farm2]);
    $violations = $location1->validate();
    $this->assertEquals(1, $violations->count());
    $this->assertInstanceOf(AssetMovementFarm::class, $violations->get(0)->getConstraint());

    // Delete the movement log and confirm that both assets now validate.
    $log->delete();
    $violations = $asset->validate();
    $this->assertEquals(0, $violations->count());
    $violations = $location1->validate();
    $this->assertEquals(0, $violations->count());
  }

  /**
   * Test group assignment constraints.
   */
  public function testGroupAssignmentConstraints() {
    $entity_type_manager = $this->container->get('entity_type.manager');
    $asset_storage = $entity_type_manager->getStorage('asset');
    $log_storage = $entity_type_manager->getStorage('log');
    $organization_storage = $entity_type_manager->getStorage('organization');

    // Create two farm organizations.
    $farm1 = $organization_storage->create([
      'type' => 'farm',
      'name' => $this->randomMachineName(),
    ]);
    $farm1->save();
    $farm2 = $organization_storage->create([
      'type' => 'farm',
      'name' => $this->randomMachineName(),
    ]);
    $farm2->save();

    // Create two group assets, one in each farm.
    $group1 = $asset_storage->create([
      'type' => 'group',
      'name' => $this->randomMachineName(),
      'farm' => [$farm1],
    ]);
    $group1->save();
    $group2 = $asset_storage->create([
      'type' => 'group',
      'name' => $this->randomMachineName(),
      'farm' => [$farm2],
    ]);
    $group2->save();

    // Create an asset in the first farm.
    $asset = $asset_storage->create([
      'type' => 'test',
      'name' => $this->randomMachineName(),
      'farm' => [$farm1],
    ]);

    // Confirm that the asset validates.
    $violations = $asset->validate();
    $this->assertEquals(0, $violations->count());

    // Save the asset.
    $asset->save();

    // Create a log that assigns the asset to group 2.
    $log = $log_storage->create([
      'type' => 'test',
      'asset' => [$asset],
      'group' => [$group2],
      'is_group_assignment' => TRUE,
    ]);

    // Confirm that a LogAssetFarm constraint violation was added because the
    // asset is not in the same farm as group 2.
    $violations = $log->validate();
    $this->assertEquals(1, $violations->count());
    $this->assertInstanceOf(LogAssetFarm::class, $violations->get(0)->getConstraint());

    // Change the log group to group 1.
    $log->set('group', [$group1]);

    // Confirm that the log validates.
    $violations = $log->validate();
    $this->assertEquals(0, $violations->count());

    // Save the log.
    $log->save();

    // Attempt to change the asset to the second farm and confirm that an
    // AssetGroupAssignmentFarm constraint violation was added because the asset
    // has a group assignment log associated with it.
    $asset->set('farm', [$farm2]);
    $violations = $asset->validate();
    $this->assertEquals(1, $violations->count());
    $this->assertInstanceOf(AssetGroupAssignmentFarm::class, $violations->get(0)->getConstraint());

    // Attempt to change group 1 to the second farm and confirm that an
    // AssetGroupAssignmentFarm constraint violation was added because the
    // group asset has a group assignment log associated with it.
    $group1->set('farm', [$farm2]);
    $violations = $group1->validate();
    $this->assertEquals(1, $violations->count());
    $this->assertInstanceOf(AssetGroupAssignmentFarm::class, $violations->get(0)->getConstraint());

    // Delete the group assignment log and confirm that both assets now
    // validate.
    $log->delete();
    $violations = $asset->validate();
    $this->assertEquals(0, $violations->count());
    $violations = $group1->validate();
    $this->assertEquals(0, $violations->count());
  }

}
