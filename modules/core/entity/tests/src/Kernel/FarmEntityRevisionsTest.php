<?php

declare(strict_types=1);

namespace Drupal\Tests\farm_entity\Kernel;

use Drupal\Core\Entity\EntityInterface;
use Drupal\KernelTests\KernelTestBase;
use PHPUnit\Framework\Attributes\Group;
use PHPUnit\Framework\Attributes\RunTestsInSeparateProcesses;

/**
 * Tests farmOS entity revisions.
 */
#[Group('farm')]
#[RunTestsInSeparateProcesses]
class FarmEntityRevisionsTest extends KernelTestBase {

  /**
   * {@inheritdoc}
   */
  protected $profile = 'farm';

  /**
   * {@inheritdoc}
   */
  protected static $modules = [
    'asset',
    'entity',
    'farm_entity',
    'farm_entity_test',
    'farm_field',
    'fraction',
    'log',
    'options',
    'plan',
    'quantity',
    'state_machine',
    'taxonomy',
    'user',
  ];

  /**
   * {@inheritdoc}
   */
  protected function setUp():void {
    parent::setUp();
    $this->installEntitySchema('asset');
    $this->installEntitySchema('log');
    $this->installEntitySchema('plan');
    $this->installEntitySchema('quantity');
    $this->installConfig(['farm_entity_test']);
  }

  /**
   * Test farmOS entity revisions.
   */
  public function testFarmEntityRevisions() {

    // Define the entity types and bundles we want to test.
    $entity_types = [
      'asset' => 'test',
      'log' => 'test',
      'plan' => 'test',
      'quantity' => 'test',
    ];

    // Test that new revisions are automatically created whenever an entity is
    // saved.
    foreach ($entity_types as $entity_type => $bundle) {
      $storage = \Drupal::entityTypeManager()->getStorage($entity_type);
      $entity = $storage->create([
        'name' => 'Test',
        'type' => $bundle,
      ]);
      $entity->save();
      $this->assertCount(1, $this->revisionIds($entity));
      $entity->save();
      $this->assertCount(2, $this->revisionIds($entity));
    }

  }

  /**
   * Loads all revision IDs of an entity sorted by revision ID descending.
   *
   * This is copied+modified from RevisionControllerTrait::revisionIds().
   *
   * @param \Drupal\Core\Entity\EntityInterface $entity
   *   The entity.
   *
   * @return mixed[]
   *   Returns a list of revision IDs.
   */
  protected function revisionIds(EntityInterface $entity) {
    $entity_type = $entity->getEntityType();
    $result = \Drupal::entityTypeManager()->getStorage($entity_type->id())->getQuery()
      ->allRevisions()
      ->condition($entity_type->getKey('id'), $entity->id())
      ->sort($entity_type->getKey('revision'), 'DESC')
      ->accessCheck(FALSE)
      ->execute();
    return array_keys($result);
  }

}
